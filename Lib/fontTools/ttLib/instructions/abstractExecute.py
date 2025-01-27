import statements
import sys
import time
import os
import psutil
import intermediateCode as IR
import copy
import logging
from fontTools.ttLib.compiler import ast
from fontTools.ttLib.data import dataType

CURSOR_UP = '\x1b[1A'
ERASE = '\x1b[2K'


class IdentifierGenerator(object):
    def generateIdentifier(self, tag, number):
        return '$' + tag + '_' + str(number)


logger = logging.getLogger(" ")
identifierGenerator = IdentifierGenerator()


class Environment(object):
    """Abstractly represents the global environment at a single point in time.

    The global environment consists of a Control Variable Table (CVT) and
    storage area, as well as a program stack.

    The cvt consists of a dict mapping locations to 16-bit signed
    integers.

    The storage_area consists of a dict mapping locations to 32-bit numbers
    [again, same comment as for cvt_table].

    The program stack abstractly represents the program stack. This is the
    critical part of the abstract state, since TrueType consists of an
    stack-based virtual machine.

    """

    def __init__(self, bytecodeContainer, tag):
        self.bytecodeContainer = bytecodeContainer
        # cvt: location -> Value
        self.cvt = copy.copy(bytecodeContainer.cvt_table)
        self.tag = tag
        # storage_area: location -> Value
        self.storage_area = {}
        self.set_graphics_state_to_default()
        # this is the TT VM stack, not the call stack
        self.program_stack = []
        self.minimum_stack_depth = None
        self.current_instruction = None
        self.current_instruction_intermediate = []
        self.keep_abstract = True
        self.already_seen_jmpr_targets = {}

        self.program_stack_changes = []

        self.pop_counter = 0

    def __repr__(self):
        stackVars = []
        STACK_LIMIT = 6
        for i in self.program_stack[-STACK_LIMIT:]:
            stackVars.append(i.data)
        stackRep = str(stackVars[-STACK_LIMIT:])
        if (len(self.program_stack) > STACK_LIMIT):
            stackRep = '[..., ' + stackRep[1:]
        return str('storage = ' + str(self.storage_area) +
                   ', graphics_state = ' + str(self.graphics_state)
                   + ', program_stack = ' + stackRep + ', program_stack_length = ' + str(len(self.program_stack)))

    def __deepcopy__(self, memo):
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result
        for k, v in self.__dict__.items():
            if k == 'current_instruction' or k == 'bytecodeContainer':
                setattr(result, k, v)
            else:
                setattr(result, k, copy.deepcopy(v, memo))
        return result

    def __eq__(self, other):
        return (self.program_stack == other.program_stack and
                self.storage_area == other.storage_area and
                self.graphics_state == other.graphics_state)

    def __ne__(self, other):
        return not self.__eq__(other)

    def merge(self, environment2):
        '''
        merge environment2 into this one; used at control-flow (e.g. if-else, jrox) merge.
        '''
        assert len(environment2.program_stack) == len(
            self.program_stack), "attempted to merge environments with different stack sizes"

        new_stack = []
        for (v1, v2) in zip(self.program_stack, environment2.program_stack):
            if (v1 == v2):
                new_stack.append(v1)
            elif isinstance(v1, IR.Variable) and isinstance(v2, IR.Variable) and v1.identifier == v2.identifier:
                new_stack.append(v1)
            else:
                new_stack.append(dataType.UncertainValue([v1, v2]))
        self.program_stack = new_stack

        for item in environment2.storage_area:
            if item not in self.storage_area:
                self.storage_area[item] = environment2.storage_area[item]
        '''
        deal with Graphics state
        '''
        for gs_key in self.graphics_state:
            if self.graphics_state[gs_key] != environment2.graphics_state[gs_key]:
                logger.info("graphics_state %s became uncertain", gs_key)
                new_graphics_state = set()
                if(type(self.graphics_state[gs_key]) is dataType.UncertainValue):
                    new_graphics_state.update(
                        self.graphics_state[gs_key].possibleValues)
                else:
                    new_graphics_state.add(self.graphics_state[gs_key])
                if(type(environment2.graphics_state[gs_key]) is dataType.UncertainValue):
                    new_graphics_state.update(
                        environment2.graphics_state[gs_key].possibleValues)
                else:
                    new_graphics_state.add(environment2.graphics_state[gs_key])
                self.graphics_state[gs_key] = dataType.UncertainValue(
                    list(new_graphics_state))
                logger.info("possible values are %s", str(
                    self.graphics_state[gs_key].possibleValues))

    def pretty_print(self, fd):
        if fd:
            fd.write(self.__repr__()+"\n")
        else:
            print self.__repr__()

    def set_graphics_state_to_default(self):
        self.graphics_state = {
            'pv':                (1, 0),  # Unit vector along the X axis.
            'fv':                (1, 0),
            'dv':                (1, 0),
            'rp':                [0, 0, 0],
            'zp':                [1, 1, 1],
            # 'controlValueCutIn': 17/16, #(17 << 6) / 16, 17/16 as an f26dot6.
            # 'deltaBase':         9,
            # 'deltaShift':        3,
            # 'minDist':           1, #1 << 6 1 as an f26dot6.
            'loop':               1,
            # 'roundPhase':        1,
            # 'roundPeriod':       1,#1 << 6,1 as an f26dot6.
            # 'roundThreshold':    0.5,#1 << 5, 1/2 as an f26dot6.
            # 'roundSuper45':      False,
            'autoFlip':          True
        }

    def write_storage_area(self, index, value):
        self.storage_area[index] = value

    def read_storage_area(self, index):
        return self.storage_area[index]

    def stack_top_name(self, offset=0):
        return identifierGenerator.generateIdentifier(self.tag, self.stack_depth() + offset)

    def generate_assign_variable(self, var, data):
        self.current_instruction_intermediate.append(
            IR.CopyStatement(var, data))

    def stack_depth(self):
        return len(self.program_stack)

    def program_stack_push(self, data=None, assign=True, customVar=None):
        if customVar:
            tempVariable = customVar
        else:
            tempVariableName = self.stack_top_name(1)
            tempVariable = IR.Variable(tempVariableName, data)
        if data is not None and assign:
            self.generate_assign_variable(tempVariable, data)

        self.program_stack.append(tempVariable)

        return tempVariable

    def program_stack_pop(self):
        self.pop_counter += 1
        val = self.program_stack.pop()
        if self.stack_depth() < self.minimum_stack_depth:
            self.minimum_stack_depth = self.stack_depth()
        return val

    def program_stack_pop_many(self, num):
        last_val = []
        for i in range(num):
            last_val.append(self.program_stack_pop())
        if self.stack_depth() < self.minimum_stack_depth:
            self.minimum_stack_depth = self.stack_depth()
        return last_val

    def replace_locals_with_formals(self):
        new_stack = []
        stack_depth = len(self.program_stack)
        for i in range(0, len(self.program_stack)):
            s = self.program_stack[i]
            if isinstance(s, IR.Variable):
                new_stack.append(IR.Variable("arg$%d" %
                                             (stack_depth - i - 1), s.data))
            else:
                new_stack.append(s)
        self.program_stack = new_stack

    def unary_operation(self, action):
        self.program_stack_changes.extend(["read", "pop", "push"])
        v_name = self.stack_top_name()
        arg = self.program_stack_pop()
        v = IR.Variable(v_name, arg)
        e = IR.UnaryExpression(v, action)
        res = e.eval(self.keep_abstract)
        self.program_stack_push(res, False)
        self.current_instruction_intermediate.append(
            IR.OperationAssignmentStatement(v, e))

        return res

    def binary_operation(self, action):
        self.program_stack_changes.extend(
            ["read", "read", "pop", "pop", "push"])
        op1_var = self.stack_top_name()
        op1_val = self.program_stack_pop()
        op2_var = self.stack_top_name()
        op2_val = self.program_stack_pop()
        if isinstance(op1_val.eval(False), int) and isinstance(op2_val.eval(False), int):
            op1 = op1_val.eval(False)
            op2 = op2_val.eval(False)
        else:
            op1 = op1_val.eval(self.keep_abstract)
            op2 = op2_val.eval(self.keep_abstract)
        expression = None
        if action is 'MAX' or action is 'MIN':
            e = IR.PrefixBinaryExpression
        else:
            e = IR.InfixBinaryExpression

        if isinstance(op1, dataType.AbstractValue) or isinstance(op2, dataType.AbstractValue):
            res = e(op1, op2, action)
            expression = e(op1_var, op2_var, getattr(IR, action+'Operator')())
        elif action is 'ADD':
            res = op1 + op2
            expression = e(op1, op2, IR.ADDOperator())
        elif action is 'SUB':
            res = op1 - op2
            # TODO: is this needed? seems unnecessary.
            if isinstance(op1_val.data, int) and isinstance(op2_val.data, int):
                res = op1_val.eval(False) - op2_val.eval(False)
            expression = e(op1, op2, IR.SUBOperator())
        elif action is 'GT':
            res = op1 > op2
            expression = e(op1, op2, IR.GTOperator())
        elif action is 'GTEQ':
            res = op1 >= op2
            expression = e(op1, op2, IR.GTEQOperator())
        elif action is 'AND':
            res = op1 and op2
            expression = e(op1, op2, IR.ANDOperator())
        elif action is 'OR':
            res = op1 or op2
            expression = e(op1, op2, IR.OROperator())
        elif action is 'MUL':
            res = op1 * op2
            expression = e(op1, op2, IR.MULOperator())
        elif action is 'DIV':
            res = op2 / op1
            expression = e(op1, op2, IR.DIVOperator())
        elif action is 'EQ':
            res = op1 == op2
            expression = e(op1, op2, IR.EQOperator())
        elif action is 'NEQ':
            res = op1 != op2
            expression = e(op1, op2, IR.NEQOperator())
        elif action is 'LT':
            res = op1 < op2
            expression = e(op1, op2, IR.LTOperator())
        elif action is 'LTEQ':
            res = op1 <= op2
            expression = e(op1, op2, IR.LTEQOperator())
        elif action is 'MAX':
            res = max(op1, op2)
            expression = e(op1, op2, IR.MAXOperator())
        elif action is 'MIN':
            res = min(op1, op2)
            expression = e(op1, op2, IR.MINOperator())
        else:
            raise NotImplementedError

        var = self.program_stack_push(res, False)
        self.current_instruction_intermediate.append(
            IR.OperationAssignmentStatement(var, expression))

    def exec_PUSH(self):
        for item in self.current_instruction.data:
            self.program_stack_changes.append("push")
            self.program_stack_push(item.value)
            var_name = self.stack_top_name(1)

    def exec_PUSHB(self):
        self.exec_PUSH()

    def exec_PUSHW(self):
        self.exec_PUSH()

    def exec_NPUSHB(self):
        self.exec_PUSH()

    def exec_NPUSHW(self):
        self.exec_PUSH()

    # Don't execute any cfg-related instructions
    # This has the effect of "executing both branches" when we hit the EIF and go back to the ELSE

    # I add this for Intermediate code of IF/ELSE/EIF, for they are just strings,could be modified later
    # Statement Objects later
    def exec_IF(self):
        pass

    def exec_EIF(self):
        pass

    def exec_ELSE(self):
        pass

    def exec_ENDF(self):
        self.current_instruction_intermediate.append(IR.ReturnStatement())

    def exec_AA(self):  # AdjustAngle
        self.program_stack_changes.extend(["read", "pop"])
        arg = self.program_stack_pop()
        self.current_instruction_intermediate.append(IR.AAMethodCall([arg]))

    def exec_ABS(self):  # Absolute
        self.unary_operation('abs')

    def exec_ADD(self):
        self.binary_operation('ADD')

    def exec_ALIGNPTS(self):
        '''
        move to points, has no further effect on the stack
        '''
        self.program_stack_changes.extend(["read", "read", "pop", "pop"])
        args = self.program_stack_pop_many(2)
        self.current_instruction_intermediate.append(
            IR.ALIGHPTSMethodCall(args))

    def exec_ALIGNRP(self):
        loopValue = self.graphics_state['loop']
        self.graphics_state['loop'] = 1
        assert len(self.program_stack) >= loopValue, "IP: stack underflow"
        pts = self.program_stack_pop_many(loopValue)
        for k in range(0, loopValue):
            self.program_stack_changes.append("read")
        for k in range(0, loopValue):
            self.program_stack_changes.append("pop")
        self.current_instruction_intermediate.append(
            IR.ALIGNRPMethodCall(pts, loop_value=loopValue))

    def exec_AND(self):
        self.binary_operation('AND')

    def exec_CEILING(self):
        self.unary_operation('ceil')

    def exec_CINDEX(self):  # CopyXToTopStack
        # index starts from 1
        index = self.program_stack_pop().eval(False)
        new_top = self.program_stack[-index].eval(self.keep_abstract)
        self.program_stack_push(new_top, False)

        # modified argN_name
        var_name = identifierGenerator.generateIdentifier(
            self.tag, self.stack_depth())
        argN_name = identifierGenerator.generateIdentifier(
            self.tag, self.stack_depth() - (index))
        self.current_instruction_intermediate.append(IR.CopyStatement(IR.Variable(var_name),
                                                                      IR.Variable(argN_name)))

        self.program_stack_changes.extend(["read", "pop"])
        for i in range(0, index):
            self.program_stack_changes.append("read")
        self.program_stack_changes.append("push")

    def exec_CLEAR(self):  # ClearStack
        for i in range(0, len(self.program_stack)):
            self.program_stack_changes.append("read")
        for i in range(0, len(self.program_stack)):
            self.program_stack_changes.append("pop")
        self.program_stack = []

    def exec_DEBUG(self):  # DebugCall
        self.program_stack_changes.extend(["read", "pop"])
        self.program_stack_pop()
        #raise NotImplementedError

    def exec_DELTA(self, op):
        # we need this number concretely to proceed
        number = self.program_stack_pop().eval(False)
        assert not isinstance(number, dataType.AbstractValue)
        loopValue = (2*number)
        args = self.program_stack_pop_many(loopValue)
        self.current_instruction_intermediate.append(
            IR.DELTAMethodCall(op, args))
        for i in range(0, 2*number):
            self.program_stack_changes.append("read")
        for i in range(0, 2*number):
            self.program_stack_changes.append("pop")

    def exec_DELTAC1(self):  # DeltaExceptionC1
        self.exec_DELTA("C1")

    def exec_DELTAC2(self):  # DeltaExceptionC2
        self.exec_DELTA("C2")

    def exec_DELTAC3(self):  # DeltaExceptionC3
        self.exec_DELTA("C3")

    def exec_DELTAP1(self):  # DeltaExceptionC1
        self.exec_DELTA("P1")

    def exec_DELTAP2(self):  # DeltaExceptionC2
        self.exec_DELTA("P2")

    def exec_DELTAP3(self):  # DeltaExceptionC3
        self.exec_DELTA("P3")

    def exec_DEPTH(self):  # GetDepthStack
        # is incorrect in the presence of method calls
        # read the whole stack???
        depth = len(self.program_stack)
        self.program_stack_push(depth)
        self.program_stack_changes.append("push")
        #raise NotImplementedError

    def exec_DIV(self):  # Divide
        self.binary_operation('DIV')

    def exec_DUP(self):
        self.program_stack_changes.extend(["read", "push"])
        v = IR.Variable(self.stack_top_name())
        top = self.program_stack[-1].eval(self.keep_abstract)
        self.program_stack_push(top, False)
        vnew = IR.Variable(self.stack_top_name())
        self.current_instruction_intermediate.append(IR.CopyStatement(vnew, v))

    def exec_FLIPOFF(self):
        self.graphics_state['autoFlip'] = False
        self.current_instruction_intermediate.append(
            IR.CopyStatement(IR.AutoFlip(), IR.Boolean('false')))

    def exec_FLIPON(self):
        self.graphics_state['autoFlip'] = True
        self.current_instruction_intermediate.append(
            IR.CopyStatement(IR.AutoFlip(), IR.Boolean('true')))

    def exec_FLIPPT(self):
        loopValue = self.graphics_state['loop']
        self.graphics_state['loop'] = 1
        assert len(self.program_stack) >= loopValue, "IP: stack underflow"
        self.program_stack_pop_many(loopValue)
        for i in range(0, loopValue):
            self.program_stack_changes.append("read")
        for i in range(0, loopValue):
            self.program_stack_changes.append("pop")
        #raise NotImplementedError

    def exec_FLIPRGOFF(self):
        self.program_stack_changes.extend(["read", "read", "pop", "pop"])
        args = self.program_stack_pop_many(2)
        self.current_instruction_intermediate.append(
            IR.FLIPRGMethodCall("off", args))

    def exec_FLIPRGON(self):
        self.program_stack_changes.extend(["read", "read", "pop", "pop"])
        args = self.program_stack_pop_many(2)
        self.current_instruction_intermediate.append(
            IR.FLIPRGMethodCall("on", args))

    def exec_FLOOR(self):
        self.unary_operation('floor')

    def exec_GC(self):
        self.program_stack_changes.extend(["read", "pop", "push"])
        arg = self.program_stack_pop()
        var = self.program_stack_push(dataType.AbstractValue(), False)
        self.current_instruction_intermediate.append(IR.GCMethodCall(
            self.current_instruction.data[0].value, [arg], var))

    def exec_GETINFO(self):
        '''
        if h.stack[-1]&(1<<0) != 0:
        #Set the engine version. We hard-code this to 35, the same as
        #the C freetype code, which says that "Version~35 corresponds
        #to MS rasterizer v.1.7 as used e.g. in Windows~98".
        res |= 35

        if h.stack[-1]&(1<<5) != 0:
        #Set that we support grayscale.
        res |= 1 << 12

        #We set no other bits, as we do not support rotated or stretched glyphs.
        h.stack[-1] = res
        '''
        self.program_stack_changes.extend(["read", "pop", "push"])
        v = IR.Variable(self.stack_top_name())
        op = self.program_stack_pop()
        e = IR.GETINFOMethodCall([v])
        res = e.eval(self.keep_abstract)
        self.program_stack_push(v, False)
        self.current_instruction_intermediate.append(
            IR.OperationAssignmentStatement(v, res))

    def exec_GPV(self):
        self.program_stack_changes.extend(["push", "push"])
        op1 = self.graphics_state['pv'][0]
        op2 = self.graphics_state['pv'][1]
        pv0 = self.program_stack_push(op1, assign=False)
        pv1 = self.program_stack_push(op2, assign=False)
        self.current_instruction_intermediate.append(
            IR.CopyStatement(pv0, IR.ProjectionVectorByComponent(0)))
        self.current_instruction_intermediate.append(
            IR.CopyStatement(pv1, IR.ProjectionVectorByComponent(1)))

    def exec_GFV(self):
        self.program_stack_changes.extend(["push", "push"])
        op1 = self.graphics_state['fv'][0]
        op2 = self.graphics_state['fv'][1]
        fv0 = self.program_stack_push(op1, assign=False)
        fv1 = self.program_stack_push(op2, assign=False)
        self.current_instruction_intermediate.append(
            IR.CopyStatement(fv0, IR.FreedomVectorByComponent(0)))
        self.current_instruction_intermediate.append(
            IR.CopyStatement(fv1, IR.FreedomVectorByComponent(1)))

    def exec_GT(self):
        self.binary_operation('GT')

    def exec_GTEQ(self):
        self.binary_operation('GTEQ')

    def exec_IDEF(self):
        raise NotImplementedError

    def exec_INSTCTRL(self):
        selector = self.program_stack[-1].data
        value = self.program_stack[-2].data
        self.program_stack_pop_many(2)
        self.program_stack_changes.extend(["read", "read", "pop", "pop"])
        self.current_instruction_intermediate.append(
            IR.CopyStatement(IR.InstructControl(selector), value))

    def exec_IP(self):
        loopValue = self.graphics_state['loop']
        self.graphics_state['loop'] = 1
        assert len(self.program_stack) >= loopValue, "IP: stack underflow"
        pts = self.program_stack_pop_many(loopValue)
        self.current_instruction_intermediate.append(IR.IPMethodCall(pts))
        for i in range(0, loopValue):
            self.program_stack_changes.append("read")
        for i in range(0, loopValue):
            self.program_stack_changes.append("pop")

    def exec_ISECT(self):
        args = self.program_stack_pop_many(5)
        self.program_stack_changes.extend(
            ["read", "read", "read", "read", "read", "pop", "pop", "pop", "pop", "pop"])
        self.current_instruction_intermediate.append(IR.ISECTMethodCall(args))

    def exec_IUP(self):  # drawing-only
        self.current_instruction_intermediate.append(
            IR.IUPMethodCall(self.current_instruction.data[0]))

    def fetch_body_for_tag(self, tag):
        fpgm_prefix = "fpgm_"
        if tag.startswith(fpgm_prefix):
            fn = int(tag[len(fpgm_prefix):])
            return self.bytecodeContainer.function_table[fn].body
        else:
            return self.bytecodeContainer.tag_to_programs[self.tag].body

    def evaluate_operations(self, arg):
        """
        Helper function to simplify arg. Returns a pair indicating whether
        arg is explicit and the value produced.
        """
        if isinstance(arg, IR.UnaryExpression):
            if arg.operator == 'NEG':
                return (True, -arg.arg)
        return (False, None)

    def adjust_succ_for_relative_jump(self, current_instruction, arg, if_else_stack, ignored_insts, function_instructions_list, bytecode2ir, executor):
        # find the instructions and set the PC
        # returns (True, _) if we broke a cycle
        # also returns the jump successor

        # The cross_list records the control flow instructions crossed
        flow_control_insts_cross_list = []
        skip_list = []

        # Find the index of current_instruction
        ins = self.fetch_body_for_tag(self.tag).instructions
        pc = 0
        for i in range(len(ins)):
            if current_instruction.id == ins[i].id:
                break
            pc += 1
        assert pc < len(ins)

        # Check offset argument
        if isinstance(arg, dataType.AbstractValue):
            (explicit, arg) = self.evaluate_operations(arg)
            if not explicit:
                print("Relative jump offset is not explicit. Exiting.")
                sys.exit()

        assert not isinstance(arg, dataType.AbstractValue)

        mag = abs(arg)
        if arg < 0:
            dir = -1
        else:
            dir = 1

        # Every occurrence of
        # i    JROT[ ]/JROF[ ]
        # gets replaced by
        # i    IF[ ]
        # i+1  JMPR[ ]
        # i+2  ELSE[ ]
        # i+3  POP[ ]
        # i+4  EIF[ ]
        # Consequently, if this JMPR was originally a JROT/JROF, adjust the offset accordingly.
        if current_instruction.is_from_conditional_jump:
            mag += 3 if dir == 1 else 1

        def instruction_size(instruction):
            size = 1
            if instruction.mnemonic in ["NPUSHB", "NPUSHW"]:
                size += 1
            if instruction.mnemonic not in ["SHP", "SVTCA"]:
                for d in instruction.data:
                    size += 2 if d.is_word else 1
            return size

        # Move PC by offset, marking skipped instructions
        if dir == -1:
            while mag > 0 and pc > 0:
                pc -= 1
                crossing_instruction = ins[pc]
                mag -= instruction_size(crossing_instruction)
                if mag > 0:
                    # When mag == 0, this instruction is the target (and isn't skipped).
                    skip_list.append(crossing_instruction)
                    if crossing_instruction.mnemonic in ["IF", "ELSE", "EIF"]:
                        flow_control_insts_cross_list.append(
                            crossing_instruction)
        else:
            while mag > 0 and pc < len(ins):
                crossing_instruction = ins[pc]
                mag -= instruction_size(crossing_instruction)
                # If this is the last instruction in the list, and we skip it, this jump is essentially a return.
                if pc == len(ins) - 1 and mag == 0:
                    # TODO: this was in the original code, but doesn't do anything. we may need to use this somewhere?
                    jump_to_return = True
                    break
                pc += 1
                skip_list.append(crossing_instruction)
                if crossing_instruction.mnemonic in ["IF", "ELSE", "EIF"]:
                    flow_control_insts_cross_list.append(crossing_instruction)
        assert mag == 0, "Failed to translate relative jump"

        target = ins[pc]
        current_instruction.target = target
        # TODO: I think this case is only an infinite loop if the branch is backward. If it's forward, there's no loop.
        if len(flow_control_insts_cross_list) == 0:
            print 'while (TRUE){'
            for i in range(1, len(skip_list)):
                print '    ', skip_list[-i].id, ' : ', skip_list[-i]
            print '}'
            sys.exit('infinite loop detected, quit!')

        # only interested in jumps which cross control flow instructions
        if len(flow_control_insts_cross_list) > 0:
            # figure out whether we're in an if/else block, and if so, the block type & current branch
            in_block = False
            block_type = 'THEN'
            in_branch = 'THEN'

            if len(if_else_stack) > 0:
                in_block = True
                current_block = executor.if_else_stack[-1]
                if len(current_block.if_stmt.successors) == 3:
                    block_type = 'ELSE'
                if current_block.IR.mode == 'ELSE':
                    in_branch = 'ELSE'

            # go through each flow control instruction crossed
            # if jump backwards
            if dir == -1:
                # remove the blocks in all layers which the jump instruction crosses all the way over
                list_stack = []
                for instruction in flow_control_insts_cross_list:
                    list_stack.append(instruction)
                    while len(list_stack) > 1:
                        if list_stack[-1].mnemonic == 'IF' and list_stack[-2].mnemonic == 'EIF':
                            list_stack.pop()
                            list_stack.pop()
                        elif len(list_stack) > 2 and list_stack[-1].mnemonic == 'IF' and list_stack[-2].mnemonic == 'ELSE' and list_stack[-3].mnemonic == 'EIF':
                            list_stack.pop()
                            list_stack.pop()
                            list_stack.pop()
                        else:
                            break

                flow_control_insts_cross_list = list_stack
                num_of_layers_crossed = len([inst for inst in flow_control_insts_cross_list if inst.mnemonic == 'IF'])

                # the max layers a jump instruction can cross is the number of layer of itself
                if num_of_layers_crossed > len(if_else_stack)+1:
                    num_of_layers_crossed = len(if_else_stack)+1

                # if num_of_layers_crossed>0,the outer most layer of If/Else block will be regarded as a while loop
                if num_of_layers_crossed > 0:
                    # if the it jumps back out 1 or more layers, and crosses some if/else block's ELSE statment
                    if flow_control_insts_cross_list[-1].mnemonic == 'ELSE':
                        this_if_stmt = flow_control_inst[-1].IF
                        this_eif_stmt = this_if_stmt.successors[2]
                        flow_control_inst[-1].vest = this_eif_stmt
                        executor.ignored_insts.add(current_instruction)
                        executor.ignored_insts.add(
                            current_instruction.predecessor)
                    else:

                        # initlize and setup a set of Loop_statement, Endloop_statement and  LoopBlock ir
                        if_else_block = executor.if_else_stack[-num_of_layers_crossed]
                        loop_stmt = statements.all.LOOP_Statement()
                        loop_stmt.id = if_else_block.if_stmt.id

                        endloop_stmt = statements.all.ENDLOOP_Statement()
                        endloop_stmt.loop_stmt = loop_stmt
                        condition = if_else_block.IR.condition
                        loopIR = IR.LoopBlock(
                            condition, 'TRUE', if_else_block.IR.nesting_level)
                        loop_stmt.LOOP_BLOCK = loopIR
                        loopIR.statement_id = if_else_block.if_stmt.id
                        # executor.ignored_insts.add(current_instruction.predecessor)
                        # construct instructions list of loop body

                        if if_else_block.IR.mode == 'THEN':
                            upper_index = len(if_else_block.IR.if_instructions)
                            # if num_of_layers_crossed == len(if_else_stack):
                            #      upper_index -= 1
                            #      executor.ignored_insts.add(if_else_block.IR.if_instructions[-1])
                            for ind in range(1, upper_index):
                                if not if_else_block.IR.if_instructions[ind] in executor.ignored_insts:
                                    loopIR.loop_instructions.append(
                                        if_else_block.IR.if_instructions[ind])
                            # loopIR.loop_instructions.extend(if_else_block.IR.if_instructions[1:upper_index])
                            # add this part of code into ignored list
                            for i in range(0, upper_index):
                                executor.ignored_insts.add(
                                    if_else_block.IR.if_instructions[i])
                            loopIR.loop_size = len(
                                if_else_block.IR.if_instructions)-1

                        else:
                            loopIR.mode = 'FALSE'
                            upper_index = len(
                                if_else_block.IR.else_instructions)
                            # if num_of_layers_crossed == len(if_else_stack):
                            #    upper_index -= 1
                            #    executor.ignored_insts.add(if_else_block.IR.else_instructions[upper_index])

                            for ind in range(1, upper_index):
                                if not if_else_block.IR.else_instructions[ind] in executor.ignored_insts:
                                    loopIR.loop_instructions.append(
                                        if_else_block.IR.else_instructions[ind])
                            # add this part of code into ignored list
                            for i in range(0, upper_index):
                                executor.ignored_insts.add(
                                    if_else_block.IR.else_instructions[i])

                            loopIR.loop_size = len(
                                if_else_block.IR.else_instructions)

                        # if the jump instruction jumps out 1 layer,append the instructions outside this layer of if
                        # to the body of while loop
                        if num_of_layers_crossed == 1:
                            tmp = skip_list[-1]
                            while tmp.id != loopIR.statement_id:
                                loopIR.loop_instructions.append(tmp)
                                if tmp.mnemonic == 'IF':
                                    tmp = tmp.successors[len(tmp.successors)-1]
                                else:
                                    tmp = tmp.successors[0]

                        # construct else instructions for loop
                        if len(if_else_block.if_stmt.successors) == 3:
                            if if_else_block.IR.mode == 'THEN':
                                else_inst = if_else_block.if_stmt.successors[1]
                                while else_inst.id != if_else_block.if_stmt.successors[2].id:
                                    else_inst = else_inst.successors[0]
                                    loopIR.else_instructions.append(else_inst)
                                    executor.ignored_insts.add(else_inst)
                            else:
                                loopIR.else_instructions.extend(
                                    if_else_block.IR.if_instructions[1:])
                                for i in range(1, len(if_else_block.IR.if_instructions)):
                                    executor.ignored_insts.add(
                                        if_else_block.IR.if_instructions[i])

                        target.vest = endloop_stmt
                        #if_else_block.if_stmt.vest = endloop_stmt
                        while_loop_stack = Executor.While_Loop_stack(
                            loopIR, loop_stmt)
                        # replace the if_else_stack with while_loop_stack
                        if_else_stack[-num_of_layers_crossed] = while_loop_stack

                        for index in range(0, len(function_instructions_list)):
                            # replace if statement with the while statement
                            if function_instructions_list[index].id == if_else_block.if_stmt.id:
                                function_instructions_list[index] = loop_stmt
                        endloop_stmt.successors.append(if_else_block.if_stmt.successors[len(
                            if_else_block.if_stmt.successors)-1].successors[0])

                        # remove the jump instruction and target in this case
                        executor.ignored_insts.add(current_instruction)
                        # if num_of_layers_crossed > 1:
                        #  if if_else_stack[-1].IR.mode == 'THEN':
                        #     if_else_stack[-1].IR.if_instructions.pop()
                        #  else:
                        #     if_else_stack[-1].IR.else_instructions.pop()

                        flag = 0
                        if num_of_layers_crossed > 1:
                            flag = 1
                        for i in range(0, num_of_layers_crossed-1):
                            s = if_else_stack.pop()
                            block = s.IR
                            for inst in block.if_instructions:
                                if inst.mnemonic == 'IF':
                                    if(inst.id != s.if_stmt.id):
                                        block.if_branch.append(
                                            inst.If_Else_Block)
                                else:
                                    if not inst in executor.ignored_insts:
                                        block.if_branch.extend(
                                            bytecode2ir[inst.id])
                                if inst.id != s.if_stmt.id:
                                    executor.ignored_insts.add(inst)

                            for inst in block.else_instructions:
                                if inst.mnemonic == 'IF':
                                    block.else_branch.append(
                                        inst.If_Else_Block)
                                else:
                                    if not inst in executor.ignored_insts:
                                        block.else_branch.extend(
                                            bytecode2ir[inst.id])
                                executor.ignored_insts.add(inst)
                            # append the loop instructions outside of the outer most IF block to the inner most IF/ELSE block
                            # if the jump instruction jumps out more than 1 layer
                            # if  flag == 1:
                            if flag:
                                flag = 0
                                k = 1
                                tmp = skip_list[-k]
                                # the inner if else block should break if
                                # the if condition is not satisfied, the break
                                # layer depends on the nested loop level
                                block.break_indicator = True
                                break_layers = 0
                                for i in range(1, num_of_layers_crossed):
                                    if(isinstance(if_else_stack[-i].IR, IR.LoopBlock)):
                                        break_layers += 1
                                block.break_layer = break_layers

                                while tmp.id != loopIR.statement_id:
                                    if block.mode == 'THEN':
                                        block.if_instructions.append(tmp)
                                        block.if_branch.extend(
                                            bytecode2ir[tmp.id])
                                    else:
                                        block.else_instructions.append(tmp)
                                        block.else_branch.extend(
                                            bytecode2ir[tmp.id])
                                    k += 1
                                    tmp = skip_list[-k]

                            # when poping off an if-else-block from the stack, if this is a nested one
                            # append its IR to the parent if/else block
                            if len(if_else_stack) > 0:
                                nested_block = if_else_stack[-1].IR
                                if nested_block.mode == 'TRUE':
                                    nested_block.loop_instructions.append(
                                        s.if_stmt)
                                elif nested_block.mode == 'THEN':
                                    nested_block.if_instructions.append(
                                        s.if_stmt)
                                elif nested_block.mode == 'ELSE':
                                    nested_block.else_instructions.append(
                                        s.if_stmt)
                                executor.ignored_insts.add(s.if_stmt)

                        # if the jump instruction which jumps backwards does not cross any layer,(even though it crosses some flow control instructions)
                else:
                                # if this jump is in an if/else block
                                # check if it jumps crosses over the else instruction of current if/else block
                    if in_block:
                        for i in range(0, len(flow_control_insts_cross_list)):
                            cross_else = 0
                            if flow_control_insts_cross_list[i].id == if_else_stack[-1].if_stmt.successors[1].id:
                                    # this jumps crosses is in an if/else block,and it does not jump out any layer,but crosses the else statement of the
                                    # if/else block it's in ,  set the vest of the else to the corresponding EIF statement
                                flow_control_insts_cross_list[i].vest = if_else_stack[-1].if_stmt.successors[2]
                                # can remove the jump instruction and the target in this case
                                executor.ignored_insts.add(current_instruction)
                                executor.ignored_insts.add(
                                    if_else_stack[-1].IR.else_instructions[-1])
                                cross_else = 1
                        if not cross_else:

                            print 'WHILE (TRUE):{'
                            for i in range(1, len(skip_list)):
                                print '    ', skip_list[-i].id, ' : ', skip_list[-i]
                            print '}'
                            sys.exit('infinite loop detected, quit!')

                    else:
                        print 'WHILE (TRUE):{'
                        for i in range(1, len(skip_list)):
                            print'    ', skip_list[-i].id, ' : ', skip_list[-i]
                        print '}'
                        sys.exit('infinite loop detected, quit!')

            # if jump forwards
            elif dir == 1:
                # remove all pairs of (IF,EIF,(ELSE)) the jump instruction crossed as when dir == -1
                list_stack = []
                for i in range(0, len(flow_control_insts_cross_list)):
                    list_stack.append(flow_control_insts_cross_list[i])
                    while len(list_stack) > 1:
                        if list_stack[-1].mnemonic == 'EIF' and list_stack[-2].mnemonic == 'IF':
                            list_stack.pop()
                            list_stack.pop()
                        elif len(list_stack) > 2 and list_stack[-1].mnemonic == 'EIF' and list_stack[-2].mnemonic == 'ELSE' and list_stack[-3].mnemonic == 'IF':
                            list_stack.pop()
                            list_stack.pop()
                            list_stack.pop()
                        else:
                            break
                flow_control_insts_cross_list = list_stack
                num_of_layers_crossed = len([inst for inst in flow_control_insts_cross_list if inst.mnemonic == 'EIF'])

                if num_of_layers_crossed == 0:
                    if in_block:
                        # does not jump out any layer,but crosses its own else
                        for i in range(0, len(flow_control_insts_cross_list)):
                            if flow_control_insts_cross_list[i].id == if_else_stack[-1].if_stmt.successors[1].id:
                                if_else_stack[-1].if_stmt.successors[2].vest = flow_control_insts_cross_list[i]
                                # can remove the jump instruction and jump target in this case
                                executor.ignored_insts.add(current_instruction)
                                executor.ignored_insts.add(
                                    if_else_stack[-1].IR.if_instructions[-1])
                if num_of_layers_crossed == 0 and current_instruction.is_re_arranged:
                    if_stmt = current_instruction.re_arrange_IF
                    executor.stored_environments = if_stmt.stored_environments
                    executor.environment = copy.deepcopy(if_stmt.environment)
                    if not if_stmt.current_func_tree is None:
                        executor.current_func_tree = copy.deepcopy(
                            if_stmt.current_func_tree)
                    if_stmt.If_Else_Block.mode = 'THEN'
                    executor.ignored_insts = if_stmt.ignored_insts
                    executor.stored_environments[if_stmt.id] = if_stmt.environment
                    executor.already_seen_insts = if_stmt.already_seen_insts
                    executor.already_seen_insts.add(if_stmt.id)
                    executor.if_else_stack[-1].state = 1
                    if_stmt.set_num_pop = 1
                    executor.if_else_stack[-1].env_on_exit = None

                    # re-connect if instructions
                    itr = if_stmt
                    for i in range(1, len(if_else_stack[-1].IR.if_instructions)-1):
                        itr.successors[0] = if_else_stack[-1].IR.if_instructions[i]
                        itr = if_else_stack[-1].IR.if_instructions[i]
                    itr.successors[0] = if_else_stack[-1].IR.if_instructions[-1].target

                    # re-connect else instructions
                    itr = if_stmt.successors[1]
                    extra_pop = itr.successors[0]
                    itr.successors[0] = itr.successors[0].successors[0]
                    itr.successors[0].predecessor = itr
                    while not itr.id == current_instruction.predecessor.id:
                        itr = itr.successors[0]
                    itr.successors[0] = extra_pop
                    extra_pop.predecessor = itr
                    extra_pop.successors[0] = if_stmt.successors[2]
                    #itr.successors[0] = if_stmt.successors[2]
                    if_stmt.successors[2].successors[0] = target
                    itr = target
                    while not target.vest is None:
                        itr = itr.vest
                    itr.vest = if_stmt.successors[2]
                    itr.vest.vest = if_stmt.successors[1]
                    target = if_stmt.successors[0]

                    target.vest = None
                    target.vest = None
                    # sys.exit()

                if num_of_layers_crossed > 0:
                    if in_block:
                        s = if_else_stack[-1].if_stmt
                        itr = target
                        while not itr.vest == None:
                            itr = itr.vest
                        #itr.vest = s.successors[-1]
                        # executor.ignored_insts.add(current_instruction.predecessor)
                    if num_of_layers_crossed > 0:
                        if if_else_stack[-num_of_layers_crossed].IR.mode == 'THEN':
                            # if len(s.successors) == 2
                            if len(if_else_stack[-num_of_layers_crossed].if_stmt.successors) == 2:
                                ghost_else = statements.all.ELSE_Statement()
                                eif = executor.if_else_stack[-num_of_layers_crossed].if_stmt.successors[-1]
                                If = executor.if_else_stack[-num_of_layers_crossed].if_stmt
                                eif.If = If
                                ghost_else.successors.append(eif.successors[0])
                                ghost_else.id = 'GHOST'
                                eif.successors[0] = target
                                target.predecessor.successors[0] = eif
                                if len(If.successors) == 2:
                                    If.successors[1] = ghost_else
                                    If.successors.append(eif)
                                if num_of_layers_crossed == 1:
                                    target.vest = ghost_else
                                else:
                                    if len(executor.if_else_stack[-1].if_stmt.successors) == 2 or executor.if_else_stack[-1].IR.mode == 'ELSE':
                                        target.vest = if_else_stack[-1].if_stmt.successors[-1]
                                    else:
                                        target.vest = if_else_stack[-1].if_stmt.successors[1]
                                    eif.vest = ghost_else
                                executor.ignored_insts.add(
                                    current_instruction.predecessor)
                                executor.ignored_insts.add(current_instruction)
                            else:
                                if_stmt = executor.if_else_stack[-num_of_layers_crossed].if_stmt
                                else_stmt = if_stmt.successors[1]
                                eif_stmt = if_stmt.successors[2]
                                eif_stmt.If = if_stmt
                                itr = eif_stmt
                                while not itr.id == target.id:
                                    itr = itr.successors[0]
                                    if itr.mnemonic == 'JMPR':
                                        itr.is_re_arranged = True
                                        itr.re_arrange_IF = if_stmt
                                itr = else_stmt
                                while itr.successors[0].id != eif_stmt.id:
                                    itr = itr.successors[0]
                                itr.successors[0] = eif_stmt.successors[0]
                                target.predecessor.successors[0] = eif_stmt
                                eif_stmt.successors[0] = target

                                if num_of_layers_crossed == 1:
                                    itr = target
                                    while not itr.vest is None:
                                        itr = itr.vest
                                    itr.vest = else_stmt
                                else:
                                    if len(executor.if_else_stack[-1].if_stmt.successors) == 2 or executor.if_else_stack[-1].IR.mode == 'ELSE':
                                        target.vest = if_else_stack[-1].if_stmt.successors[-1]
                                    else:
                                        target.vest = if_else_stack[-1].if_stmt.successors[1]
                                    eif_stmt.vest = else_stmt
                                # executor.ignored_insts.add(current_instruction.predecessor)
                                # executor.ignored_insts.add(current_instruction)
                        else:
                            if_stmt = executor.if_else_stack[-num_of_layers_crossed].if_stmt
                            else_stmt = if_stmt.successors[1]
                            eif_stmt = if_stmt.successors[2]
                            # 1.restore the environment to the env right before else

                            executor.environment = copy.deepcopy(
                                executor.if_else_stack[-num_of_layers_crossed].env_on_exit)
                            if not executor.if_else_stack[-num_of_layers_crossed].current_func_tree is None:
                                executor.current_func_tree = copy.deepcopy(
                                    executor.if_else_stack[-num_of_layers_crossed].current_func_tree)
                            vest = statements.all.RESTORE_AND_SETVEST_Statement()
                            vest.env_id = current_instruction.id
                            setvest = None
                            if len(executor.if_else_stack[-1].if_stmt.successors) == 2 or executor.if_else_stack[-1].IR.mode == 'ELSE':
                                setvest = if_else_stack[-1].if_stmt.successors[-1]
                            else:
                                setvest = if_else_stack[-1].if_stmt.successors[1]
                            vest.setvest = setvest
                            tmp = eif_stmt.successors[0]
                            eif_stmt.successors[0] = target
                            target.vest = vest
                            itr = tmp
                            tmp_stack = []
                            while not itr.id == target.id:
                                if len(tmp_stack) == 0:

                                    itr.if_block_layer = num_of_layers_crossed
                                    if itr.mnemonic == 'IF':
                                        itr.if_block_layer += 1
                                    if target.mnemonic == 'ENDF':
                                        itr.if_block_layer += 1
                                if itr.mnemonic == 'IF' or itr.mnemonic == 'ELSE' or itr.mnemonic == 'EIF':
                                    tmp_stack.append(itr)
                                if len(tmp_stack) > 1:
                                    if tmp_stack[-1].mnemonic == 'EIF' and tmp_stack[-2].mnemonic == 'IF':
                                        tmp_stack.pop()
                                        tmp_stack.pop()
                                    else:
                                        if len(tmp_stack) > 2:
                                            if tmp_stack[-1].mnemonic == 'EIF' and tmp_stack[-1].mnemonic == 'ELSE' and tmp_stack[-1].mnemonic == 'IF':
                                                tmp_stack.pop()
                                                tmp_stack.pop()
                                                tmp_stack.pop()
                                itr = itr.successors[0]

                            target = tmp

        logger.info("relative jump target is %s" % ins[pc])

        current_instruction.successors = []
        if target not in self.current_instruction.successors:
            self.already_seen_jmpr_targets.setdefault(self.tag, [])
            if not target in self.already_seen_jmpr_targets[self.tag]:
                current_instruction.successors.append(target)
                self.already_seen_jmpr_targets[self.tag].append(target)
            else:
                return target
        # if len(target.successors)>0:
            #print 'the next of jump target:',target.successors[0],target.successors[0].id
        return target

    def exec_ENDLOOP(self):
        pass

    def exec_JMPR(self):
        pass

    def exec_JROF(self):
        pass

    def exec_JROT(self):
        pass

    def exec_LT(self):
        self.binary_operation('LT')

    def exec_LTEQ(self):
        self.binary_operation('LTEQ')

    def exec_MAX(self):
        self.binary_operation('MAX')

    def exec_MD(self):
        self.program_stack_changes.extend(
            ["read", "read", "pop", "pop", "push"])
        args = self.program_stack_pop_many(2)
        #assert isinstance(op1, dataType.PointValue) and (op1, dataType.PointValue)
        res = dataType.Distance()
        self.program_stack_push(res, assign=False)
        self.current_instruction_intermediate.append(
            IR.MDMethodCall(self.current_instruction.data[0], args))

    def exec_MDAP(self):
        self.program_stack_changes.extend(["read", "pop"])
        arg = self.program_stack_pop().eval(self.keep_abstract)
        self.current_instruction_intermediate.append(
            IR.MDAPMethodCall(self.current_instruction.data[0], [arg]))

    def exec_MDRP(self):
        self.program_stack_changes.extend(["read", "pop"])
        arg = self.program_stack_pop().eval(self.keep_abstract)
        self.current_instruction_intermediate.append(
            IR.MDRPMethodCall(self.current_instruction.data[0], [arg]))

    def exec_MIAP(self):
        self.program_stack_changes.extend(["read", "read", "pop", "pop"])
        args = self.program_stack_pop_many(2)
        self.current_instruction_intermediate.append(
            IR.MIAPMethodCall(self.current_instruction.data[0], args))

    def exec_MIN(self):
        self.binary_operation('MIN')

    def exec_MINDEX(self):
        self.program_stack_changes.extend(["read", "pop"])
        index = self.program_stack_pop().eval(False)
        for i in range(0, index-1):
            self.program_stack_changes.append("read")
        # self.program_stack_changes.append("push")
        assert not isinstance(index, dataType.AbstractValue)
        top = self.program_stack[-index].eval(self.keep_abstract)
        del self.program_stack[-index]
        self.program_stack_push(top, False)
        tmp_name = identifierGenerator.generateIdentifier(
            self.tag, self.stack_depth() + 1)
        arg1_name = identifierGenerator.generateIdentifier(
            self.tag, self.stack_depth())
        argN_name = identifierGenerator.generateIdentifier(
            self.tag, self.stack_depth() - (index - 1))
        self.current_instruction_intermediate.append(IR.CopyStatement(IR.Variable(tmp_name),
                                                                      IR.Variable(arg1_name)))
        self.current_instruction_intermediate.append(IR.CopyStatement(IR.Variable(arg1_name),
                                                                      IR.Variable(argN_name)))
        for i in range(index-1, 1, -1):
            arg_name = identifierGenerator.generateIdentifier(
                self.tag, self.stack_depth() - i + 1)
            argi_name = identifierGenerator.generateIdentifier(
                self.tag, self.stack_depth() - i + 2)
            self.current_instruction_intermediate.append(IR.CopyStatement(IR.Variable(arg_name),
                                                                          IR.Variable(argi_name)))

        arg_name = identifierGenerator.generateIdentifier(
            self.tag, self.stack_depth() - index + 1)
        self.current_instruction_intermediate.append(IR.CopyStatement(IR.Variable(arg_name),
                                                                      IR.Variable(tmp_name)))

    def exec_MIRP(self):
        self.program_stack_changes.extend(["read", "read", "pop", "pop"])
        args = self.program_stack_pop_many(2)
        self.current_instruction_intermediate.append(
            IR.MIRPMethodCall(self.current_instruction.data[0], args))

    def exec_MPPEM(self):
        self.program_stack_changes.extend(["push"])
        data = None
        if self.graphics_state['pv'] == (0, 1):
            data = dataType.PPEM_Y()
        else:
            data = dataType.PPEM_X()

        var = self.stack_top_name(1)
        # self.current_instruction_intermediate.append(IR.CopyStatement(IR.Variable(var),data))
        self.program_stack_push(data)

    def exec_MPS(self):
        self.program_stack_changes.append("push")
        var = self.stack_top_name(1)
        self.program_stack_push(dataType.PointSize())
        self.current_isntruction_intermediate.append(
            IR.CopyStatement(IR.Variable(var), dataType.PointSize))

    def exec_MSIRP(self):
        self.program_stack_changes.extend(["read", "read", "pop", "pop"])
        args = self.program_stack_pop_many(2)
        self.current_instruction_intermediate.append(
            IR.MSIRPMethodCall(self.current_instruction.data[0], args))

    def exec_MUL(self):
        self.binary_operation('MUL')

    def exec_NEG(self):
        self.unary_operation('NEG')
        '''
        arg = self.program_stack_pop()
        narg = IR.UnaryExpression(arg, IR.NEGOperator()).eval(self.keep_abstract)
        self.program_stack_push(narg)
	'''

    def exec_NEQ(self):
        self.binary_operation('NEQ')

    def exec_NOT(self):
        self.unary_operation('not')

    def exec_NROUND(self):
        raise NotImplementedError

    def exec_ODD(self):
        raise NotImplementedError

    def exec_OR(self):
        self.binary_operation('OR')

    def exec_POP(self):
        self.program_stack_changes.append("pop")
        self.program_stack_pop()

    def exec_RCVT(self):
        self.program_stack_changes.extend(["read", "pop", "push"])
        op = self.program_stack_pop().eval(self.keep_abstract)
        # XXX should be done from dataType & eval
        # or, we could accept that we basically never really know the CVT table.

        res_var = IR.ReadFromIndexedStorage("cvt_table", op)
        if self.keep_abstract or isinstance(op, dataType.AbstractValue):
            res = IR.ReadFromIndexedStorage("cvt_table", op)
        else:
            res = self.cvt[op]
        self.program_stack_push(res, False)
        self.current_instruction_intermediate.append(IR.CopyStatement
                                                     (IR.Variable(self.stack_top_name()),
                                                      res_var))

    def exec_RDTG(self):
        self.current_instruction_intermediate.append(
            IR.CopyStatement(IR.RoundState(), dataType.RoundState_DTG()))

    def exec_ROFF(self):
        self.current_instruction_intermediate.append(IR.ROFFMethodCall())

    def exec_ROLL(self):
        self.program_stack_changes.extend(["read", "read", "read"])
        tmp = self.program_stack[-1]
        self.program_stack[-1] = self.program_stack[-3]
        self.program_stack[-3] = self.program_stack[-2]
        self.program_stack[-2] = tmp

        tmp_name = identifierGenerator.generateIdentifier(
            self.tag, self.stack_depth() + 1)
        arg1_name = identifierGenerator.generateIdentifier(
            self.tag, self.stack_depth())
        arg2_name = identifierGenerator.generateIdentifier(
            self.tag, self.stack_depth() - 1)
        arg3_name = identifierGenerator.generateIdentifier(
            self.tag, self.stack_depth() - 2)

        self.current_instruction_intermediate.append(IR.CopyStatement(IR.Variable(tmp_name),
                                                                      IR.Variable(arg1_name)))
        self.current_instruction_intermediate.append(IR.CopyStatement(IR.Variable(arg1_name),
                                                                      IR.Variable(arg3_name)))
        self.current_instruction_intermediate.append(IR.CopyStatement(IR.Variable(arg3_name),
                                                                      IR.Variable(arg2_name)))
        self.current_instruction_intermediate.append(IR.CopyStatement(IR.Variable(arg2_name),
                                                                      IR.Variable(tmp_name)))

    def exec_ROUND(self):
        self.program_stack_changes.extend(["read", "pop"])
        var = self.program_stack_pop()
        res = self.program_stack_push(dataType.F26Dot6(), False)
        self.current_instruction_intermediate.append(IR.ROUNDMethodCall
                                                     (self.current_instruction.data[0],
                                                      [var], res))

    def exec_RS(self):
        self.program_stack_changes.extend(["read", "pop", "push"])
        arg = self.program_stack_pop().eval(self.keep_abstract)
        if self.keep_abstract:
            self.program_stack_push(dataType.AbstractValue(), False)
            self.current_instruction_intermediate.append(
                IR.CopyStatement(IR.Variable(self.stack_top_name()),
                                 IR.ReadFromIndexedStorage("storage_area", arg)))
        else:
            res = self.read_storage_area(op)
            self.program_stack_push(res)

    def exec_RTDG(self):
        self.current_instruction_intermediate.append(
            IR.CopyStatement(IR.RoundState(), dataType.RoundState_DG()))

    def exec_RTG(self):
        self.current_instruction_intermediate.append(
            IR.CopyStatement(IR.RoundState(), dataType.RoundState_G()))

    def exec_RTHG(self):
        self.current_instruction_intermediate.append(
            IR.CopyStatement(IR.RoundState(), dataType.RoundState_HG()))

    def exec_RUTG(self):
        self.current_instruction_intermediate.append(
            IR.CopyStatement(IR.RoundState(), dataType.RoundState_UG()))

    def exec_S45ROUND(self):
        self.program_stack_changes.extend(["read", "pop"])
        self.program_stack_pop()
        #raise NotImplementedError

    def exec_SANGW(self):
        self.program_stack_changes.extend(["read", "pop"])
        self.program_stack_pop()
        #raise NotImplementedError

    def exec_SCANCTRL(self):
        value = self.program_stack[-1].data
        self.program_stack_pop()
        self.current_instruction_intermediate.append(
            IR.CopyStatement(IR.ScanControl(), value))
        self.program_stack_changes.extend(["read", "pop"])

    def exec_SCANTYPE(self):
        value = self.program_stack[-1].data
        self.program_stack_pop()
        self.current_instruction_intermediate.append(
            IR.CopyStatement(IR.ScanType(), value))
        self.program_stack_changes.extend(["read", "pop"])

    def exec_SCVTCI(self):
        self.program_stack_changes.extend(["read", "pop"])
        self.program_stack_pop()
        #raise NotImplementedError

    def exec_SDB(self):
        self.program_stack_changes.extend(["read", "pop"])
        arg = self.program_stack_pop()
        self.current_instruction_intermediate.append(IR.SDBMethodCall([arg]))

    def exec_SDPVTL(self):
        self.program_stack_changes.extend(["read", "read", "pop", "pop"])
        args = self.program_stack_pop_many(2)
        self.current_instruction_intermediate.append(
            IR.SDPVTLMethodCall(self.current_instruction.data[0], args))

    def exec_SDS(self):
        self.program_stack_changes.extend(["read", "pop"])
        arg = self.program_stack_pop()
        self.current_instruction_intermediate.append(IR.SDSMethodCall([arg]))

    def exec_SFVFS(self):
        self.program_stack_changes.extend(["read", "read", "pop", "pop"])
        args = self.program_stack_pop_many(2)
        self.current_instruction_intermediate.append(IR.SFVFSMethodCall(args))

    def exec_SFVTCA(self):
        data = int(self.current_instruction.data[0].value)
        assert (data is 1 or data is 0)
        if data == 0:
            self.graphics_state['fv'] = (0, 1)
        if data == 1:
            self.graphics_state['fv'] = (1, 0)
        self.current_instruction_intermediate.append(
            IR.CopyStatement(IR.FreedomVector(), IR.Constant(data)))

    def exec_SFVTL(self):  # Set Freedom Vector To Line
        self.program_stack_changes.extend(["read", "read", "pop", "pop"])
        args = self.program_stack_pop_many(2)
        self.current_instruction_intermediate.append(
            IR.SFVTLMethodCall(self.current_instruction.data[0], args))

    def exec_SFVTPV(self):  # Set Freedom Vector To Projection Vector
        self.graphics_state['fv'] = self.graphics_state['pv']
        self.current_instruction_intermediate.append(IR.SFVTPVMethodCall())

    def exec_SHC(self):
        self.program_stack_changes.extend(["read", "pop"])
        arg = self.program_stack_pop()
        self.current_instruction_intermediate.append(
            IR.SHCMethodCall(self.current_instruction.data[0], [arg]))

    def exec_SHP(self):
        loopValue = self.graphics_state['loop']
        self.graphics_state['loop'] = 1
        assert len(self.program_stack) >= loopValue, "IP: stack underflow"
        pts = self.program_stack_pop_many(loopValue)
        self.current_instruction_intermediate.append(
            IR.SHPMethodCall(self.current_instruction.data[0], pts))
        for i in range(0, loopValue):
            self.program_stack_changes.append("read")
        for i in range(0, loopValue):
            self.program_stack_changes.append("pop")

    def exec_SHPIX(self):
        pops = self.pop_counter
        self.program_stack_pop()
        loopValue = self.graphics_state['loop']
        self.graphics_state['loop'] = 1
        assert len(self.program_stack) >= loopValue, "IP: stack underflow"
        pts = self.program_stack_pop_many(loopValue)
        ir = IR.SHPIXMethodCall(pts)
        ir.pops = pops
        self.current_instruction_intermediate.append(ir)
        for i in range(0, loopValue):
            self.program_stack_changes.append("read")
        for i in range(0, loopValue):
            self.program_stack_changes.append("pop")

    def exec_SHZ(self):
        self.program_stack_changes.extend(["read", "pop"])
        arg = self.program_stack_pop()
        self.current_instruction_intermediate.append(
            IR.SHZMethodCall(self.current_instruction.data[0], [arg]))

    def exec_SLOOP(self):
        self.program_stack_changes.extend(["read", "pop"])
        self.graphics_state['loop'] = self.program_stack[-1].data
        arg = self.program_stack_pop()
        self.current_instruction_intermediate.append(IR.SLOOPMethodCall([arg]))

    def exec_SMD(self):
        self.program_stack_changes.extend(["read", "pop"])
        arg = self.program_stack_pop()
        self.current_instruction_intermediate.append(IR.SMDMethodCall([arg]))

    def exec_SPVFS(self):
        self.program_stack_changes.extend(["read", "read", "pop", "pop"])
        args = self.program_stack_pop_many(2)
        self.current_instruction_intermediate.append(IR.SPVFSMethodCall(args))

    def exec_SPVTCA(self):
        data = int(self.current_instruction.data[0].value)
        assert (data is 1 or data is 0)
        if data == 0:
            self.graphics_state['pv'] = (0, 1)
        if data == 1:
            self.graphics_state['pv'] = (1, 0)
        self.current_instruction_intermediate.append(
            IR.CopyStatement(IR.ProjectionVector(), IR.Constant(data)))

    def exec_SPVTL(self):
        data = self.current_instruction.data[0]
        self.program_stack_changes.extend(["read", "read", "pop", "pop"])
        args = self.program_stack_pop_many(2)
        self.current_instruction_intermediate.append(
            IR.SPVTLMethodCall(data, args))

    def exec_S45ROUND(self):
        self.program_stack_changes.extend(["read", "pop"])
        arg = dataType.RoundState_Super45(
            self.program_stack_pop().eval(self.keep_abstract))
        self.current_instruction_intermediate.append(
            IR.CopyStatement(IR.RoundState(), arg))

    def exec_SROUND(self):
        self.program_stack_changes.extend(["read", "pop"])
        arg = dataType.RoundState_Super(
            self.program_stack_pop().eval(self.keep_abstract))
        self.current_instruction_intermediate.append(
            IR.CopyStatement(IR.RoundState(), arg))

    def exec_SSW(self):
        self.program_stack_changes.extend(["read", "pop"])
        arg_name = self.stack_top_name()
        data = self.program_stack[-1].data
        self.program_stack_pop()
        self.graphics_state['singleWidthValue'] = data
        self.current_instruction_intermediate.append(
            IR.CopyStatement(IR.SingleWidthValue(), arg_name))

    def exec_SSWCI(self):
        self.program_stack_changes.extend(["read", "pop"])
        self.program_stack_pop()
        #raise NotImplementedError

    def exec_SUB(self):
        self.binary_operation('SUB')

    def exec_SVTCA(self):
        data = int(self.current_instruction.data[0].value)
        assert (data is 1 or data is 0)
        if data == 0:
            self.graphics_state['pv'] = (0, 1)
            self.graphics_state['fv'] = (0, 1)

        if data == 1:
            self.graphics_state['pv'] = (1, 0)
            self.graphics_state['fv'] = (1, 0)

        self.current_instruction_intermediate.append(
            IR.CopyStatement(IR.FreedomVector(), IR.Constant(data)))
        self.current_instruction_intermediate.append(
            IR.CopyStatement(IR.ProjectionVector(), IR.Constant(data)))

    def exec_SWAP(self):
        self.program_stack_changes.extend(["read", "read"])
        tmp = self.program_stack[-1]
        self.program_stack[-1] = self.program_stack[-2]
        self.program_stack[-2] = tmp

        tmp_name = identifierGenerator.generateIdentifier(
            self.tag, self.stack_depth() + 1)
        arg1_name = identifierGenerator.generateIdentifier(
            self.tag, self.stack_depth())
        arg2_name = identifierGenerator.generateIdentifier(
            self.tag, self.stack_depth()-1)

        self.current_instruction_intermediate.append(IR.CopyStatement(IR.Variable(tmp_name),
                                                                      IR.Variable(arg1_name)))
        self.current_instruction_intermediate.append(IR.CopyStatement(IR.Variable(arg1_name),
                                                                      IR.Variable(arg2_name)))
        self.current_instruction_intermediate.append(IR.CopyStatement(IR.Variable(arg2_name),
                                                                      IR.Variable(tmp_name)))

    def exec_SZP0(self):
        self.program_stack_changes.extend(["read", "pop"])
        arg = self.program_stack_pop().eval(False)
        assert (arg is 1 or arg is 0)
        self.current_instruction_intermediate.append(
            IR.CopyStatement(IR.ZP0(), arg))

    def exec_SZP1(self):
        self.program_stack_changes.extend(["read", "pop"])
        arg = self.program_stack_pop().eval(False)
        assert (arg is 1 or arg is 0)
        self.current_instruction_intermediate.append(
            IR.CopyStatement(IR.ZP1(), arg))

    def exec_SZP2(self):
        self.program_stack_changes.extend(["read", "pop"])
        arg = self.program_stack_pop().eval(False)
        assert (arg is 1 or arg is 0)
        self.current_instruction_intermediate.append(
            IR.CopyStatement(IR.ZP2(), arg))

    def exec_SZPS(self):
        self.program_stack_changes.extend(["read", "pop"])
        arg = self.program_stack_pop()
        zp0 = IR.ZP0()
        zp0.identifier += ".all"
        self.current_instruction_intermediate.append(
            IR.CopyStatement(zp0, arg))
        self.current_instruction_intermediate.append(
            IR.CopyStatement(IR.ZP1(), arg))
        self.current_instruction_intermediate.append(
            IR.CopyStatement(IR.ZP2(), arg))

    def exec_UTP(self):
        self.program_stack_changes.extend(["read", "pop"])
        self.program_stack_pop()
        #raise NotImplementedError

    def exec_WCVTF(self):
        res = self.getOpandVar()
        self.cvt[res[0]] = res[1]
        ir = IR.CVTStorageStatement(res[2], res[3])
        ir.unit = 'F'
        self.current_instruction_intermediate.append(ir)

    def exec_WCVTP(self):
        res = self.getOpandVar()
        self.cvt[res[0]] = res[1]
        ir = IR.CVTStorageStatement(res[2], res[3])
        ir.unit = 'P'
        self.current_instruction_intermediate.append(ir)

    def getOpandVar(self):
        self.program_stack_changes.extend(["read", "read", "pop", "pop"])
        op1 = self.program_stack[-2]
        op2 = self.program_stack[-1]
        self.program_stack_pop_many(2)

        return [op1.eval(self.keep_abstract), op2.eval(self.keep_abstract), op1, op2]

    def exec_WS(self):
        res = self.getOpandVar()
        self.current_instruction_intermediate.append(
            IR.WriteStorageStatement(res[3], res[2]))
        self.write_storage_area(res[0], res[1])

    def exec_EQ(self):
        self.binary_operation('EQ')

    def exec_SRP(self, index):  # SetRefPoint
        self.program_stack_changes.extend(["read", "pop"])
        #self.graphics_state['rp'][index] = self.program_stack[-1]
        return self.program_stack_pop()

    def exec_SRP0(self):
        pops = self.pop_counter
        arg = self.exec_SRP(0)
        ir = IR.CopyStatement(IR.RP0(), arg)
        ir.pops = pops
        self.current_instruction_intermediate.append(ir)

    def exec_SRP1(self):
        pops = self.pop_counter
        arg = self.exec_SRP(1)
        ir = IR.CopyStatement(IR.RP1(), arg)
        ir.pops = pops
        self.current_instruction_intermediate.append(ir)

    def exec_SRP2(self):
        pops = self.pop_counter
        arg = self.exec_SRP(2)
        ir = IR.CopyStatement(IR.RP2(), arg)
        ir.pops = pops
        self.current_instruction_intermediate.append(ir)

    def exec_SANGW(self):
        self.program_stack_changes.extend(["read", "pop"])
        self.program_stack_pop()
        #raise NotImplementedError

    def exec_SCFS(self):
        self.program_stack_changes.extend(["read", "read", "pop", "pop"])
        args = self.program_stack_pop_many(2)
        self.current_instruction_intermediate.append(IR.SCFSMethodCall(args))

    def exec_SCVTCI(self):
        self.program_stack_changes.extend(["read", "pop"])
        arg_name = self.stack_top_name()
        data = self.program_stack[-1].data
        self.program_stack_pop()
        self.graphics_state['controlValueCutIn'] = data
        self.current_instruction_intermediate.append(
            IR.CopyStatement(IR.SingleWidthCutIn(), arg_name))

    def exec_LOOPCALL(self):
        self.program_stack_changes.extend(["read", "read", "pop", "pop"])
        fn = self.program_stack_pop().eval(False)
        count = self.program_stack_pop().eval(False)
        print fn, count

        #self.current_instruction_intermediate.append(IR.LoopCallStatement(fn, count))

    def exec_CALL(self):
        self.program_stack_changes.extend(["read", "pop"])
        var = self.program_stack[-1]
        self.program_stack_pop()
        # self.current_instruction_intermediate.append(IR.CallStatement(var))

    def execute_current_instruction(self, ins):
        self.current_instruction_intermediate = []
        self.current_instruction = ins
        getattr(self, "exec_"+self.current_instruction.mnemonic)()
        self.program_stack_changes.append("dot")
        if not self.current_instruction.mnemonic == "POP":
            self.pop_counter = 0
        return self.current_instruction_intermediate


def erase_lines(n):
    for i in range(0, n):
        sys.stdout.write(CURSOR_UP)
        sys.stdout.write(ERASE)


class Executor(object):
    """
    Given a TrueType instruction, abstractly transform the global state.

    Produces a new global state accounting for the effects of that
    instruction. Modifies the stack, CVT table, and storage area.
    """

    def print_progress(self, func_type):
        # print in the center of text field
        def print_center(field_len, text):
            if text == "" or text is None:
                text = '--'
            if len(text) > field_len:
                shortened = text[:field_len-1]
                sys.stdout.write(shortened)
            else:
                space = (field_len - len(text))/2
                sys.stdout.write(' '*space)
                sys.stdout.write(text)
                sys.stdout.write(' '*(field_len-space-len(text)))

        font_name_len = 25
        time_len = 14
        memory_len = 14
        percentage_len = 12
        tag_len = 18
        erase_lines(self.row_to_erase)
        sys.stdout.write('-'*(font_name_len+time_len +
                              memory_len+percentage_len+tag_len+6)+'\n')
        sys.stdout.write('|')
        print_center(font_name_len, 'font_name')
        sys.stdout.write('|')
        print_center(time_len, 'time')
        sys.stdout.write('|')
        print_center(memory_len, 'memory')
        sys.stdout.write('|')
        if func_type == "prep":
            print_center(percentage_len, '%')
        else:
            print_center(percentage_len, 'glyf#')
        sys.stdout.write('|')
        print_center(tag_len, 'tag')
        sys.stdout.write('|\n')
        sys.stdout.write('-'*(font_name_len+time_len +
                              memory_len+percentage_len+tag_len+6)+'\n')

        process = psutil.Process(os.getpid())
        mem = str(process.memory_info().rss/1024/1024)+' mb'
        duration = int(time.time() - self.start_time)
        seconds = duration % 60
        minutes = duration // 60
        hours = minutes // 60
        minutes = minutes % 60
        t = str(hours) + ' h ' + str(minutes) + ' m ' + str(seconds) + ' s '

        sys.stdout.write('|')
        print_center(font_name_len, self.current_font_name)
        sys.stdout.write('|')
        print_center(time_len, t)
        sys.stdout.write('|')
        print_center(memory_len, mem)
        sys.stdout.write('|')
        if func_type == 'prep':
            per = float(self.current_progress)/float(self.program_size) * 100.0
            per = "%.2f" % per
            print_center(percentage_len, per)
        else:
            per = str(self.glyph_num)+'/'+str(self.all_glyphs)
            print_center(percentage_len, per)
        sys.stdout.write('|')
        print_center(tag_len, self.current_tag)
        sys.stdout.write('|\n')
        sys.stdout.write('-'*(font_name_len+time_len +
                              memory_len+percentage_len+tag_len+6)+'\n')
        if self.current_tag == 'prep':
            sys.stdout.write('**************** working on prep ...\n')
        else:
            sys.stdout.write('**************** working on glyph: %d/%d\n' % (self.glyph_num, self.all_glyphs))
        self.row_to_erase = 6

    class Uncertain_Callee_Backup(object):
        def __init__(self):
            self.backup_executor_status = None
            self.function_itr = 0
            self.call_stack = []
            self.possible_functions = []
            self.program_stack_backup = []
            self.arguments_recorded_functions = None
            self.largest_function = -1
            self.in_test_function = 0
            self.lower_bound = -1
            self.upper_bound = -1
            self.current_instruction_intermediate = None

        def find_largest_func(self, bytecodeContainer):
            largest = -1
            for key, value in bytecodeContainer.function_table.items():
                if key > largest:
                    largest = key

            return largest

    def __init__(self, bc):
        self.flag = 1
        self.bytecodeContainer = bc
        self.replace_uncertain_function = -1
        self.environment = Environment(bc, "")
        self.current_instruction = None
        self.maximum_stack_depth = 0
        self.call_stack = []
        self.stored_environments = {}
        self.if_else_stack = []
        # generated as a side effect:
        self.global_function_table = {}
        self.visited_functions = set()
        self.bytecode2ir = {}
        self.already_seen_insts = set()
        self.ignored_insts = set()
        self.modified_program_functions = set()
        self.first_time_call_args = {}
        self.first_time_stack_effect = {}
        # encounter an uncertain callee
        self.uncertain_callee_backup = None
        self.replace_function_table = {}
        self.uncertain_callee_delegate = {}

        # for test script
        self.all_glyphs = 0
        self.glyph_num = 0
        self.current_font_name = None
        self.current_tag = None
        self.program_size = 0
        self.current_progress = 0
        self.row_to_erase = 0
        self.start_time = None

    def __deepcopy__(self, memo):
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result
        for k, v in self.__dict__.items():
            if not (k in {'bytecodeContainer', 'uncertain_callee_backup', 'global_function_table'}):
                if k == 'call_stack':
                    #print 'copying call_stack',type(v)
                    #print type(v[0])
                    setattr(result, k, copy.deepcopy(v))
                else:
                    setattr(result, k, copy.deepcopy(v, memo))

        return result

    def num_pop(self, inst):
        dictionary = {'POP': 1, 'DELTAP1': 200}
        if inst.mnemonic in dictionary:
            if dictionary[inst.mnemonic] > 99:
                return 1 + self.environment.program_stack[-1].eval(False) * int(dictionary[inst.mnemonic]) / 100
            else:
                return dictionary[inst.mnemonic]
        else:
            return 0

    def graphics_state_initialization_code(self):
        return [
            IR.CopyStatement(IR.AutoFlip(), IR.Boolean('true')),
            IR.CopyStatement(IR.ScanControl(), IR.Constant(0)),
            IR.CopyStatement(IR.ScanType(), IR.Constant(0)),
            IR.CopyStatement(IR.SingleWidthCutIn(), IR.Constant(0)),
            IR.CopyStatement(IR.SingleWidthValue(), IR.Constant(0)),
            IR.CopyStatement(IR.FreedomVectorByComponent(0), IR.Constant(1)),
            IR.CopyStatement(IR.FreedomVectorByComponent(1), IR.Constant(1)),
            IR.CopyStatement(IR.ProjectionVector(), IR.Constant(1)),
            IR.CopyStatement(IR.LoopValue(), IR.Constant(1)),
            IR.CopyStatement(IR.InstructControl(
                IR.Constant(0)), IR.Constant(0)),
            IR.CopyStatement(IR.InstructControl(
                IR.Constant(1)), IR.Constant(0)),
            IR.CopyStatement(IR.MinimumDistance(), IR.Constant(1)),
            IR.CopyStatement(IR.RoundState(), dataType.RoundState_G()),
            IR.CopyStatement(IR.ZP0(), IR.Constant(1)),
            IR.CopyStatement(IR.ZP1(), IR.Constant(1)),
            IR.CopyStatement(IR.ZP2(), IR.Constant(1)),
            IR.CopyStatement(IR.RP0(), IR.Constant(0)),
            IR.CopyStatement(IR.RP1(), IR.Constant(0)),
            IR.CopyStatement(IR.RP2(), IR.Constant(0))
        ]

    class While_Loop_stack(object):
        def __init__(self, IR, while_stmt):
            self.IR = IR
            self.while_stmt = while_stmt

    class If_else_stack(object):
        def __init__(self, IR, if_stmt, state):
            self.IR = IR
            self.if_stmt = if_stmt
            self.state = state
            self.env_on_exit = None
            self.program_stack_changes_on_else = []

        def __deepcopy__(self, memo):
            cls = self.__class__
            result = cls.__new__(cls)
            memo[id(self)] = result
            for k, v in self.__dict__.items():
                # if k == 'IR':
                #    setattr(result, k, v)
                # else:
                setattr(result, k, copy.deepcopy(v, memo))
            return result

    def stack_depth(self):
        return self.environment.stack_depth()

    def execute_LOOPCALL(self):
        #print 'loopcall:',self.current_instruction.successors[0].id
        count = self.environment.program_stack[-2].eval(False)
        if isinstance(count, dataType.AbstractValue):
            # oops. execute once, hope it doesn't modify the stack.
            # we could also record the effects & replay them if it did (but how many times?)
            self.execute_CALL()
        else:
            cn = self.environment.program_stack[-2].eval(False)
            callee = self.environment.program_stack[-1].eval(False)
            if not self.current_instruction.id in self.bytecode2ir.keys():
                self.setIRForBytecode(self.current_instruction, [
                                      IR.LoopCallStatement(callee, cn)])
            self.execute_CALL(count, True)

    def unfold_binary_exp(self, exp, scale_flag):
        if isinstance(exp, IR.BinaryExpression):
            scale_f = scale_flag
            if exp.operator == "DIV":
                scale_f = "div"
            (left_lower, left_upper) = self.unfold_binary_exp(exp.left, scale_f)
            (right_lower, right_upper) = self.unfold_binary_exp(exp.right, scale_f)
            if exp.operator == "ADD" or exp.operator == "SUB":
                lower = None
                upper = None
                if left_lower == "inf" or right_lower == "inf":
                    lower = "inf"
                else:
                    if exp.operator == "ADD":
                        lower = left_lower + right_lower
                    else:
                        lower = left_lower - right_lower

                if left_upper == "inf" or right_upper == "inf":
                    upper = "inf"
                else:
                    if exp.operator == "ADD":
                        upper = left_upper + right_upper
                    else:
                        upper = left_upper - right_upper
                return (lower, upper)

            if exp.operator == "DIV":
                lower = None
                upper = None
                if left_lower == "inf" or right_upper == "inf":
                    lower = "inf"
                else:
                    lower = right_lower/left_upper

                if left_upper == "inf" or right_lower == "inf":
                    upper = "inf"
                else:
                    upper = right_upper/left_lower
                return (lower*64.0, upper*64.0)

            if exp.operator == "MAX" or exp.operator == "MIN":
                lower = None
                upper = None
                if left_lower == "inf" and right_lower == "inf":
                    lower = "inf"
                elif left_lower == "inf":
                    lower = right_lower
                elif right_lower == "inf":
                    lower = left_lower
                else:
                    if exp.operator == "MIN":
                        lower = min(left_lower, right_lower)
                    else:
                        lower = max(left_lower, right_lower)

                if left_upper == "inf" and right_upper == "inf":
                    upper = "inf"
                elif left_upper == "inf":
                    upper = right_upper
                elif right_upper == "inf":
                    upper = right_upper
                else:
                    if exp.operator == "MIN":
                        upper = min(left_upper, right_upper)
                    else:
                        upper = max(left_upper, right_upper)
                return (lower, upper)

        elif isinstance(exp, int):
            if scale_flag == "div":
                return (float(exp)/64.0, float(exp)/64.0)
            else:
                return (exp, exp)
        elif isinstance(exp, IR.Variable) or isinstance(exp, dataType.F26Dot6):
            return ("inf", "inf")
        else:
            return (None, None)

    def get_range(self, exp):
        if isinstance(exp, IR.BinaryExpression):
            scale_flag = None
            if exp.operator == "DIV":
                scale_flag = "div"

            (lower, upper) = self.unfold_binary_exp(exp, scale_flag)
            return (int(lower), int(upper))

    def execute_CALL(self, repeats=1, is_loopcall=False):
        # actually we *always* want to get the concrete callee
        callee = self.environment.program_stack[-1].eval(False)
        if not is_loopcall and (not self.current_instruction.id in self.bytecode2ir.keys()):
            self.setIRForBytecode(self.current_instruction, [
                                  IR.CallStatement(callee)])
        if isinstance(callee, dataType.AbstractValue):
            if self.uncertain_callee_backup == None:
                (lower_bound, upper_bound) = self.get_range(callee)
                caller = self.call_stack[-1][0]
                if self.current_instruction.id in self.uncertain_callee_delegate.keys():
                    callee = self.uncertain_callee_delegate[self.current_instruction.id]

                else:
                    backup = Executor.Uncertain_Callee_Backup()
                    backup.lower_bound = lower_bound
                    backup.upper_bound = upper_bound
                    backup.function_itr = lower_bound
                    backup.backup_executor_status = copy.deepcopy(self)
                    backup.current_instruction_intermediate = copy.deepcopy(
                        self.environment.current_instruction_intermediate)
                    backup.if_else_stack = copy.deepcopy(self.if_else_stack)
                    self.uncertain_callee_backup = backup
                    backup.backup_executor_status.current_instruction.successors = self.current_instruction.successors
                    backup.backup_executor_status.current_instruction.predecessor = self.current_instruction.predecessor
                    for i in range(0, len(self.call_stack)):

                        new_if_else_stack = backup.backup_executor_status.call_stack[i][-4]

                        for j in range(0, len(new_if_else_stack)):
                            new_if_else_stack[j].if_stmt = self.call_stack[i][-4][j].if_stmt

                        oldtuple = backup.backup_executor_status.call_stack[i]
                        newtuple = (oldtuple[0], self.call_stack[i][1], self.call_stack[i][2], oldtuple[3],
                                    oldtuple[4], oldtuple[5], new_if_else_stack, oldtuple[7], oldtuple[8], oldtuple[9])
                        backup.backup_executor_status.call_stack[i] = newtuple
                        backup.call_stack.append(self.call_stack[i][0])
                    backup.largest_function = backup.find_largest_func(
                        self.bytecodeContainer)
                    callee = backup.function_itr
                    while callee in backup.call_stack:
                        backup.function_itr += 1
                        callee = backup.function_itr

            else:
                callee = self.uncertain_callee_backup.function_itr
                if self.uncertain_callee_backup.upper_bound < callee:
                    if len(self.uncertain_callee_backup.possible_functions) > 0:
                        callee = self.uncertain_callee_backup.possible_functions[0]
                        caller = self.call_stack[-1][0]
                        self.replace_function_table[self.uncertain_callee_backup.possible_functions[0]
                                                    ] = self.uncertain_callee_backup.possible_functions
                        self.uncertain_callee_delegate[self.current_instruction.id] = self.uncertain_callee_backup.possible_functions[0]
                        self.uncertain_callee_backup = None
                    else:
                        print 'error: no possible function'
                        sys.exit()
                    self.uncertain_callee = None

                if not self.uncertain_callee_backup is None:
                    while callee in self.uncertain_callee_backup.call_stack or (not callee in self.bytecodeContainer.function_table):
                        self.uncertain_callee_backup.function_itr += 1
                        callee = self.uncertain_callee_backup.function_itr

        assert not isinstance(callee, dataType.AbstractValue)
        if not self.uncertain_callee_backup is None:

            if callee in self.uncertain_callee_backup.call_stack and self.uncertain_callee_backup.in_test_function:

                self.environment = copy.deepcopy(
                    self.uncertain_callee_backup.backup_executor_status.environment)
                self.if_else_stack = copy.deepcopy(
                    self.uncertain_callee_backup.backup_executor_status.if_else_stack)
                for i in range(0, len(self.if_else_stack)):
                    self.if_else_stack[i].if_stmt.successors = self.uncertain_callee_backup.backup_executor_status.if_else_stack[i].if_stmt.successors
                    self.if_else_stack[i].if_stmt.predecessor = self.uncertain_callee_backup.backup_executor_status.if_else_stack[i].if_stmt.predecessor

                self.current_instruction = self.uncertain_callee_backup.backup_executor_status.current_instruction
                self.maximum_stack_depth = self.uncertain_callee_backup.backup_executor_status.maximum_stack_depth
                self.call_stack = copy.deepcopy(
                    self.uncertain_callee_backup.backup_executor_status.call_stack)
                for i in range(0, len(self.uncertain_callee_backup.backup_executor_status.call_stack)):

                    new_if_else_stack = copy.deepcopy(
                        self.uncertain_callee_backup.backup_executor_status.call_stack[i][-4])

                    for j in range(0, len(new_if_else_stack)):
                        new_if_else_stack[j].if_stmt = self.uncertain_callee_backup.backup_executor_status.call_stack[i][-4][j].if_stmt

                    oldtuple = self.call_stack[i]
                    newtuple = (oldtuple[0], self.uncertain_callee_backup.backup_executor_status.call_stack[i][1], self.uncertain_callee_backup.backup_executor_status.call_stack[i]
                                [2], oldtuple[3], oldtuple[4], oldtuple[5], new_if_else_stack, oldtuple[7], oldtuple[8], oldtuple[9])
                    self.call_stack[i] = newtuple

                self.visited_functions = self.uncertain_callee_backup.backup_executor_status.visited_functions
                self.bytecode2ir = self.uncertain_callee_backup.backup_executor_status.bytecode2ir
                self.already_seen_insts = self.uncertain_callee_backup.backup_executor_status.already_seen_insts
                self.uncertain_callee_backup.function_itr += 1
                return

        # update call graph counts
        first_time_called = False
        if not callee in self.visited_functions:
            first_time_called = True
        self.visited_functions.add(callee)
        if callee not in self.global_function_table:
            self.global_function_table[callee] = 1
        else:
            self.global_function_table[callee] += 1
        # execute the call instruction itself
        tag = "fpgm_%s" % callee
        self.environment.execute_current_instruction(self.current_instruction)
        self.environment.minimum_stack_depth = self.stack_depth()

        # when first time executing a fpgm, set current function tree to this and append the expressions in this function to this func_tree
        if first_time_called:
            new_func_tree = ast.function("fpgm", None, num=callee)
            self.current_func_tree = new_func_tree
        # if this is not the first time in this fpgm, set current_func_tree to None, so no expression will be appended
        else:
            self.current_func_tree = None

        # set call stack & jump
        # yuck should regularize the CFG with tail nodes to avoid needing this hack
        if (len(self.current_instruction.successors) == 0):
            succ = None
        else:
            succ = self.current_instruction.successors[0]
        self.call_stack.append((callee, self.current_instruction, succ,
                                self.environment.tag, copy.copy(
                                    self.environment.program_stack),
                                self.stored_environments, self.if_else_stack, repeats, copy.deepcopy(self.environment.program_stack_changes), repeats))

        self.if_else_stack = []
        logger.info("in %s, calling function %d" %
                    (self.environment.tag, callee))
        assert callee in self.bytecodeContainer.function_table, "Callee function #%s not defined" % callee
        self.current_instruction = self.bytecodeContainer.function_table[callee].start(
        )
        self.current_execution_stream = self.bytecodeContainer.function_table[
            callee].execution_stream
        self.environment.tag = tag
        self.environment.replace_locals_with_formals()
        self.stored_environments = {}

    def get_num_of_arguments(self, difference):
        num_of_local_vars = 0
        consecutive_read = 0
        num_of_parameters = 0
        for i in range(0, len(difference)):
            record = difference[i]
            if record == "push":
                if consecutive_read - num_of_local_vars > num_of_parameters:
                    num_of_parameters = consecutive_read - num_of_local_vars

                consecutive_read = 0
                num_of_local_vars += 1
            if record == "pop":
                if consecutive_read - num_of_local_vars > num_of_parameters:
                    num_of_parameters = consecutive_read - num_of_local_vars
                consecutive_read = 0
                num_of_local_vars -= 1
            if record == "dot":
                if consecutive_read - num_of_local_vars > num_of_parameters:
                    num_of_parameters = consecutive_read - num_of_local_vars
                consecutive_read = 0

            if record == "read":
                consecutive_read += 1
                if i == len(difference)-1:
                    if consecutive_read - num_of_local_vars > num_of_parameters:
                        num_of_parameters = consecutive_read - num_of_local_vars
                        consecutive_read = 0
        return num_of_parameters

    def execute_RETURN(self, tag):
        self.modified_program_functions.add(self.call_stack[-1][0])
        if not self.uncertain_callee_backup is None:
            if self.uncertain_callee_backup.in_test_function == 1:
                self.uncertain_callee_backup.in_test_function = 0

        tag_returned_from = self.environment.tag

        (callee, previous_instruction, self.current_instruction,
         self.environment.tag, caller_program_stack, self.stored_environments, self.if_else_stack, repeats, program_stack_changes, cn) = self.call_stack.pop()
        difference = self.environment.program_stack_changes[len(
            program_stack_changes):]
        num_of_parameters = self.get_num_of_arguments(difference)
        is_first_visit = False
        # if not self.current_instruction == None:
        #    print 'exec return pop stack:',self.current_instruction,self.current_instruction.id
        record_arguments = False

        if tag_returned_from in self.visited_functions:
            # calling a function for a second time
            # assert that stored instructions == bytecodeContainer.IRs[tag]
            pass
        else:
            is_first_visit = True
            intermediateCodes = []
            for inst in self.bytecodeContainer.function_table[callee].instructions:
                # If this instruction is IF, append the corresponding IR.IF_ELSE_BLOCK to IntermediateCodes
                if inst not in self.ignored_insts and inst.id in self.bytecode2ir:
                    if inst.mnemonic == 'IF':
                        intermediateCodes.append(inst.If_Else_Block)
                    if inst.mnemonic == 'LOOP':
                        intermediateCodes.append(inst.LOOP_BLOCK)
                    else:
                        intermediateCodes.extend(self.bytecode2ir[inst.id])
            self.bytecodeContainer.IRs[tag_returned_from] = self.fixupDestsToIR(
                intermediateCodes)

        self.visited_functions.add(tag_returned_from)

        stack_depth_upon_call = len(caller_program_stack)
        stack_used = stack_depth_upon_call - self.environment.minimum_stack_depth
        stack_additional = self.stack_depth() - stack_depth_upon_call
        if(repeats > 1):
            # reset the cur instruction if it's loop call
            self.current_instruction = self.current_instruction.predecessor
            repeats -= 1
            # update call graph counts
            self.visited_functions.add(callee)
            if callee not in self.global_function_table:
                self.global_function_table[callee] = 1
            else:
                self.global_function_table[callee] += 1

            # execute the call instruction itself
            # self.environment.execute_current_instruction(self.current_instruction)

            self.environment.minimum_stack_depth = self.stack_depth()
            # set call stack & jump
            # yuck should regularize the CFG with tail nodes to avoid needing this hack
            if (len(self.current_instruction.successors) == 0):
                succ = None
            else:
                succ = self.current_instruction.successors[0]
            self.call_stack.append((callee, self.current_instruction, succ,
                                    self.environment.tag, copy.copy(
                                        self.environment.program_stack),
                                    self.stored_environments, self.if_else_stack, repeats, copy.deepcopy(self.environment.program_stack_changes), cn))
            self.if_else_stack = []
            logger.info("in %s, calling function %d" %
                        (self.environment.tag, callee))
            assert callee in self.bytecodeContainer.function_table, "Callee function #%s not defined" % callee
            self.current_instruction = self.bytecodeContainer.function_table[callee].start(
            )
            self.current_execution_stream = self.bytecodeContainer.function_table[
                callee].execution_stream
            self.environment.tag = "fpgm_%s" % callee
            self.environment.replace_locals_with_formals()
            self.stored_environments = {}

        # argument name modified
        call_arg_list = []
        call_args = '('
        # stack_used (previous)
        for i in range(num_of_parameters):
            if i > 0:
                call_args += ', '
            call_arg_name = identifierGenerator.generateIdentifier(
                tag, stack_depth_upon_call - i)
            call_args += call_arg_name
            call_arg_list.append(call_arg_name)
        call_args += ')'
        call_rv = ''
        if stack_additional > 0:
            call_rv += '('
            for i in range(stack_additional):
                if i > 0:
                    call_rv += ', '
                call_rv += self.environment.program_stack[-(i+1)].identifier
            call_rv += ') := '

        if repeats > 1:
            call_rv += 'LOOP'
            repeats_str = '_%s' % str(cn)
        else:
            repeats_str = ''
        if callee not in self.first_time_call_args.keys():
            self.first_time_call_args[callee] = call_arg_list
            self.first_time_stack_effect[callee] = len(
                self.environment.program_stack)-len(caller_program_stack)
        # XXX this is mis-typed; it should be a MethodCallInstruction
        #self.setIRForBytecode(previous_instruction, ['%sCALL%s %s%s' % (call_rv, repeats_str, str(callee), call_args)])
        ori_callee = callee
        if callee in self.replace_function_table.keys():
            callee = []
           # call_arg_list = []
            for fn in self.replace_function_table[ori_callee]:
                callee.append(fn)
                # call_arg_list.append(self.function_arg_list[fn])

        temp = self.bytecode2ir[previous_instruction.id][0]
        if not temp.returned:
            temp.callee = callee
            temp.call_arg_list = call_arg_list
            temp.stack_effect = len(
                self.environment.program_stack) - len(caller_program_stack)
            if isinstance(temp, IR.LoopCallStatement):
                temp.repeats = cn
            temp.returned = True

        logger.info("pop call stack, next is %s",
                    str(self.current_instruction))
        logger.info("stack used %d/stack additional %d" %
                    (stack_used, stack_additional))

    def fixupDestsToIR(self, ic):
        for inst in self.bytecodeContainer.flatten_IR(ic):
            if isinstance(inst, IR.JROxStatement) or isinstance(inst, IR.JmpStatement):
                inst.inst_dest = self.bytecode2ir[inst.bytecode_dest.id][0]
        return ic

    def setIRForBytecode(self, current_instruction, ir):
        already_seen_this_inst = current_instruction.id in self.already_seen_insts
        if not already_seen_this_inst:
            self.bytecode2ir[current_instruction.id] = ir
            self.already_seen_insts.add(current_instruction.id)
        if len(self.if_else_stack) > 0 and not already_seen_this_inst:
            if_else_block = None
            if current_instruction.if_block_layer != None:
                if_else_block = self.if_else_stack[-current_instruction.if_block_layer]
            else:
                if_else_block = self.if_else_stack[-1]
            if isinstance(if_else_block, self.If_else_stack):
                block = if_else_block.IR
                if not already_seen_this_inst:
                    if current_instruction.if_block_layer != None:
                        if current_instruction.block_type == 'THEN':
                            block.if_instructions.append(current_instruction)
                        else:
                            block.else_instructions.append(current_instruction)
                    else:
                        if block.mode == 'ELSE':
                            block.else_instructions.append(current_instruction)
                        else:
                            block.if_instructions.append(current_instruction)

    def setIRForBytecodeInExecutionStream(self, current_instruction, ir):
        self.execution_stream.append((copy.deepcopy(current_instruction), ir))

    def execute(self, tag):
        logger.info("execute; tag is %s", tag)
        self.environment.tag = str(tag)
        program = self.bytecodeContainer.tag_to_programs[tag]
        self.current_instruction = program.start()
        self.if_else_stack = []
        self.environment.minimum_stack_depth = 0
        self.current_tag = tag
        self.program_size = len(program.body.instructions)
        #largest = 0

        # show current process on 'prep'
        if not self.current_tag == 'prep':
            self.print_progress('glyf')

        while self.current_instruction is not None:
            # update and show current process on 'prep'
            if self.current_instruction.id.startswith('prep'):
                self.current_progress = int(self.current_instruction.id[5:])
                self.print_progress('prep')

            # get the deepst vest, set the current instruction to the vest and take it off
            holder = self.current_instruction
            while self.current_instruction.vest is not None:
                holder = self.current_instruction
                self.current_instruction = self.current_instruction.vest
            holder.vest = None

            # If the instruction is ENDF, but if else stack is not empty, this is caused by jump inst targeted to ENDF
            # in this case, the program structure was re-arrange and need to set the pointer to the successor of ENDF
            if self.current_instruction.mnemonic == 'ENDF' and len(self.if_else_stack) > 0:
                if len(self.current_instruction.successors) > 0:
                    self.current_instruction = self.current_instruction.successors[0]
                    continue

            # print log info
            logger.info("     program_stack is %s" % (
                str(map(lambda s: s.eval(False), self.environment.program_stack))))
            if self.current_instruction.data is not None:
                logger.info("[pc] %s->%s|%s", self.current_instruction.id,
                            self.current_instruction.mnemonic, map(lambda x: x.value, self.current_instruction.data))
            else:
                logger.info("[pc] %s->%s", self.current_instruction.id,
                            self.current_instruction.mnemonic)
            logger.info("     succs are %s",
                        self.current_instruction.successors)
            logger.info("     call_stack len is %s", len(self.call_stack))

            # CALL/LOOPCALL
            if self.current_instruction.mnemonic == 'CALL' or self.current_instruction.mnemonic == 'LOOPCALL':
                if self.current_instruction.mnemonic == 'CALL':
                    self.execute_CALL()
                else:
                    self.execute_LOOPCALL()
                continue

            # first, abstractly execute the successor statement (fallthru case)
            # but leave a breadcrumb reminding us, upon function end, to visit
            # the other branch.

            # when we collect breadcrumbs, see if we're visiting
            # new statements or already-visited statements.
            # if new, just analyze with the stored environment
            # if already-visited, need to abstractly execute with new env
            # and see if we need to change anything.

            ir = []
            is_reexecuting = False
            store_env = True

            # convert JROT and JROF to JMPR embedded in an if-else block
            # this will modify the function for future calls
            if self.current_instruction.mnemonic == 'JROT' or self.current_instruction.mnemonic == 'JROF':
                # get the instruction list of program, if in an fpgm, get the instruction of the fpgm instead
                if len(self.call_stack) > 0:
                    instructions = self.bytecodeContainer.function_table[
                        self.call_stack[-1][0]].instructions
                else:
                    instructions = program.body.instructions

                if_statement = statements.all.IF_Statement()
                jump_statement = statements.all.JMPR_Statement()
                if self.current_instruction.mnemonic == 'JROF':
                    if_statement.reverse = True
                else_statement = statements.all.ELSE_Statement()
                pop_statement = statements.all.POP_Statement()
                eif_statement = statements.all.EIF_Statement()
                import re
                cur_id = next(re.finditer(
                    r'\d+$', self.current_instruction.id)).group(0)
                prefix = self.current_instruction.id[:-len(cur_id)]
                cur_id = int(cur_id)
                if_statement.id = self.current_instruction.id

                self.current_instruction.predecessor.successors[0] = if_statement
                if_statement.add_successor(jump_statement)
                if_statement.add_successor(else_statement)
                if_statement.add_successor(eif_statement)
                jump_statement.add_successor(else_statement)
                else_statement.add_successor(pop_statement)
                pop_statement.add_successor(eif_statement)
                eif_statement.add_successor(
                    self.current_instruction.successors[0])
                else_statement.IF = if_statement
                eif_statement.IF = if_statement

                eif_statement.set_predecessor(if_statement)
                else_statement.set_predecessor(if_statement)
                jump_statement.set_predecessor(if_statement)
                pop_statement.set_predecessor(else_statement)
                if_statement.predecessor = self.current_instruction.predecessor
                self.current_instruction.successors[0].set_predecessor(
                    eif_statement)

                start_id = int(
                    next(re.finditer(r'\d+$', instructions[0].id)).group(0))
                current_index = instructions.index(self.current_instruction)
                instructions.remove(self.current_instruction)
                instructions.insert(current_index, if_statement)
                instructions.insert(current_index+1, jump_statement)
                instructions.insert(current_index+2, else_statement)
                instructions.insert(current_index+3, pop_statement)
                instructions.insert(current_index+4, eif_statement)
                for i in range(0, len(instructions)):
                    instructions[i].id = prefix + str(start_id + i)

                self.current_instruction = if_statement

                jump_statement.is_from_conditional_jump = True
                continue

            if self.current_instruction.mnemonic == 'IF':
                if len(self.if_else_stack) > 0 and self.if_else_stack[-1].if_stmt == self.current_instruction and self.if_else_stack[-1].state > 0:
                    logger.info("succs %d state %d" % (
                        len(self.current_instruction.successors), self.if_else_stack[-1].state))
                    is_reexecuting = True
                    if self.if_else_stack[-1].state+1 == len(self.current_instruction.successors):
                        self.current_instruction.num_pop = self.current_instruction.set_num_pop
                        self.current_instruction.set_num_pop = 0
                        # no more branches
                        # dont restore the environemnt to env_on_exit here
                        if len(self.if_else_stack[-1].if_stmt.successors) == 3:
                            len_of_stack_before_func = 0
                            if len(self.call_stack) > 0:
                                len_of_stack_before_func = len(
                                    self.call_stack[-1][8])
                            difference1 = self.environment.program_stack_changes[
                                len_of_stack_before_func:]
                            difference2 = self.if_else_stack[-1].program_stack_changes_on_else[len_of_stack_before_func:]
                            args1 = self.get_num_of_arguments(difference1)
                            args2 = self.get_num_of_arguments(difference2)
                            if args2 > args1:
                                self.environment.program_stack_changes = self.if_else_stack[
                                    -1].program_stack_changes_on_else

                        store_env = False
                        logger.info("entering if block (getting out) for %s@%s, stack height is %d" % (
                            str(cond), self.current_instruction.id, len(self.environment.program_stack)))

                    else:
                        # back at the if and have more branches...

                        # should not restore the environment here, since this work has been done when processing
                        # the successors, and according to the logic of this if-else-block, this will also be
                        # executed when quiting the if_else_block,which is not supposed to happen

                        #self.environment = copy.deepcopy(self.stored_environments[self.current_instruction.id])
                        logger.info("entering if block (repeat) for %s@%s, stack height is %d" % (
                            str(cond), self.current_instruction.id, len(self.environment.program_stack)))

                else:

                    for i in range(0, self.current_instruction.num_pop):
                        self.environment.program_stack.pop(-2)
                    # first time round at this if statement...
                    self.environment.program_stack_changes.extend(
                        ["read", "pop"])

                    if len(self.call_stack) > 0:
                        if (not self.call_stack[-1][0] in self.modified_program_functions) and len(self.environment.program_stack) > 1:
                            itr = self.current_instruction.successors[0]
                            store_if_instruction = 0
                            while not itr.id == self.current_instruction.successors[-1].id:
                                if itr.mnemonic == 'JMPR':
                                    store_if_instruction = 1
                                    break
                                itr = itr.successors[0]
                            if store_if_instruction:
                                self.current_instruction.stored_environments = copy.deepcopy(
                                    self.stored_environments)
                                self.current_instruction.already_seen_insts = copy.deepcopy(
                                    self.already_seen_insts)
                                self.current_instruction.ignored_insts = copy.deepcopy(
                                    self.ignored_insts)
                                self.current_instruction.bytecode2ir = copy.deepcopy(
                                    self.bytecode2ir)
                                self.current_instruction.environment = copy.deepcopy(
                                    self.environment)
                                self.current_instruction.environment.program_stack.pop()
                                self.current_instruction.environment.program_stack.pop()
                                if not self.current_func_tree is None:
                                    self.current_instruction.current_func_tree = copy.deepcopy(
                                        self.current_func_tree)
                                self.flag = 0

                    cond = self.environment.program_stack.pop()
                    logger.info("entering if block (first time) for %s, stack height is %d" % (
                        str(cond), self.stack_depth()))
                    newBlock = IR.IfElseBlock(cond,
                                              len(self.if_else_stack) + 1)
                    self.current_instruction.If_Else_Block = newBlock
                    newBlock.reverse = self.current_instruction.reverse

                    self.if_else_stack.append(self.If_else_stack(
                        newBlock, self.current_instruction, 0))

            elif self.current_instruction.mnemonic == 'ELSE':
                is_reexecuting = True
                block = self.if_else_stack[-1].IR
                block.mode = 'ELSE'

            if store_env:
                if not is_reexecuting and self.current_instruction.id in self.stored_environments:
                    # If the same EIF is pointed for the second time,the current env should not be merged with
                    # the env of EIF
                    #print self.current_instruction.id
                    if self.current_instruction.mnemonic != 'EIF':
                        if not len(self.environment.program_stack) == len(self.stored_environments[self.current_instruction.id].program_stack):
                            print 'this function does not work!!', len(self.environment.program_stack), len(
                                self.stored_environments[self.current_instruction.id].program_stack)
                            sys.exit()
                        else:
                            self.environment.merge(
                                self.stored_environments[self.current_instruction.id])
                            is_reexecuting = True
                else:
                    # reduce the memory and time usages, only deep copy the environments for key instructions
                    if self.current_instruction.mnemonic in ['IF', 'ELSE', 'JROT', 'JROF', 'JMPR']:
                        self.stored_environments[self.current_instruction.id] = copy.deepcopy(
                            self.environment)

            if self.current_instruction.mnemonic == 'JMPR':
                logger.info("     program_stack is %s" % (
                    str(map(lambda s: s.eval(False), self.environment.program_stack))))
                #	self.current_instruction.vest = self.current_instruction.successors[0]
                dest = self.environment.program_stack_pop().eval(keep_abstract=False)
                instructions_list = program.body.instructions
                if len(self.call_stack) > 0:
                    callee = self.call_stack[-1][0]
                    instructions_list = self.bytecodeContainer.function_table[callee].instructions
                branch_succ = self.environment.adjust_succ_for_relative_jump(
                    self.current_instruction, dest, self.if_else_stack, self.ignored_insts, instructions_list, self.bytecode2ir, self)
                logger.info("     adjusted succs now %s",
                            self.current_instruction.successors)

            ir.extend(self.environment.execute_current_instruction(
                self.current_instruction))
            if self.stack_depth() > self.maximum_stack_depth:
                self.maximum_stack_depth = self.stack_depth()
            self.setIRForBytecode(self.current_instruction, ir)

            # normal case: 1 succ
            if len(self.current_instruction.successors) == 1:
                # do we have if/else succs to explore?
                if self.current_instruction.mnemonic == 'EIF' or self.current_instruction.mnemonic == 'ELSE':
                    if len(self.if_else_stack) == 0:
                        self.current_instruction = self.current_instruction.successors[0]
                        continue
                    assert len(self.if_else_stack) > 0
                    if self.current_instruction.mnemonic == 'ELSE' and self.if_else_stack[-1].state == 2:
                        for i in range(0, self.current_instruction.IF.num_pop):
                            self.environment.program_stack.pop(-2)
                        self.current_instruction = self.current_instruction.successors[0]
                    else:
                        if self.current_instruction.mnemonic == 'EIF' and isinstance(self.if_else_stack[-1].IR, IR.LoopBlock):

                            block = self.if_else_stack[-1].IR
                            for inst in block.loop_instructions:
                                if inst.mnemonic == 'IF':
                                    block.loop_ir.append(inst.If_Else_Block)
                                else:
                                    block.loop_ir.extend(
                                        self.bytecode2ir[inst.id])
                                    self.ignored_insts.add(inst)

                            for inst in block.else_instructions:
                                if inst.mnemonic == 'IF':
                                    block.else_ir.append(inst.If_Else_Block)
                                else:
                                    block.else_ir.extend(
                                        self.bytecode2ir[inst.id])
                                    self.ignored_insts.add(inst)

                            self.current_instruction = self.current_instruction.successors[0]

                        else:
                            # return to the closest enclosing IF, which then jumps to ELSE/EIF
                            self.current_instruction = self.if_else_stack[-1].if_stmt
                            logger.info("env_on_exit is %s" % self.environment)
                            if self.if_else_stack[-1].env_on_exit is None:
                                self.if_else_stack[-1].program_stack_changes_on_else = copy.deepcopy(
                                    self.environment.program_stack_changes)
                                self.if_else_stack[-1].env_on_exit = copy.copy(
                                    self.environment)

                            else:
                                # should only merge the environment when quitting a if_else_block, the previous code
                                # merge the environement at anytime executing 'EIF' or 'ELSE',except the first time of
                                # 'ELSE' for ELSE mode, or the first time of 'EIF' for IF mode correspondingly
                                if self.if_else_stack[-1].state == len(self.if_else_stack[-1].if_stmt.successors):
                                    if len(self.if_else_stack[-1].env_on_exit.program_stack) == len(self.environment.program_stack):
                                        self.if_else_stack[-1].env_on_exit.merge(
                                            self.environment)
                                    else:
                                        print 'this function does not work,restore executor status...'
                                        if self.uncertain_callee_backup == None:
                                            print "wrong (%s)" % self.current_tag
                                            sys.exit()
                                            return
                                        self.environment = copy.deepcopy(
                                            self.uncertain_callee_backup.backup_executor_status.environment)
                                        self.if_else_stack = copy.deepcopy(
                                            self.uncertain_callee_backup.backup_executor_status.if_else_stack)
                                        for i in range(0, len(self.if_else_stack)):
                                            self.if_else_stack[i].if_stmt.successors = self.uncertain_callee_backup.backup_executor_status.if_else_stack[i].if_stmt.successors
                                            self.if_else_stack[i].if_stmt.predecessor = self.uncertain_callee_backup.backup_executor_status.if_else_stack[i].if_stmt.predecessor

                                        self.current_instruction = self.uncertain_callee_backup.backup_executor_status.current_instruction
                                        self.maximum_stack_depth = self.uncertain_callee_backup.backup_executor_status.maximum_stack_depth
                                        self.call_stack = copy.deepcopy(
                                            self.uncertain_callee_backup.backup_executor_status.call_stack)

                                        for i in range(0, len(self.uncertain_callee_backup.backup_executor_status.call_stack)):

                                            new_if_else_stack = copy.deepcopy(
                                                self.uncertain_callee_backup.backup_executor_status.call_stack[i][-4])

                                            for j in range(0, len(new_if_else_stack)):
                                                new_if_else_stack[j].if_stmt = self.uncertain_callee_backup.backup_executor_status.call_stack[i][-4][j].if_stmt

                                            oldtuple = self.call_stack[i]
                                            newtuple = (oldtuple[0], self.uncertain_callee_backup.backup_executor_status.call_stack[i][1], self.uncertain_callee_backup.backup_executor_status.call_stack[i]
                                                        [2], oldtuple[3], oldtuple[4], oldtuple[5], new_if_else_stack, oldtuple[7], oldtuple[8], oldtuple[9])
                                            self.call_stack[i] = newtuple

                                        self.visited_functions = self.uncertain_callee_backup.backup_executor_status.visited_functions
                                        self.bytecode2ir = self.uncertain_callee_backup.backup_executor_status.bytecode2ir
                                        self.already_seen_insts = self.uncertain_callee_backup.backup_executor_status.already_seen_insts
                                        self.uncertain_callee_backup.function_itr += 1
                                        continue
                                    # self.environment.merge(self.if_else_stack[-1].env_on_exit)

                    # restore the environement to corresponding IF instruction,only if first time executing
                    # ELSE for ELSE mode,or the first time of 'EIF' for IF mode correspondingly, the previous
                    # code did this for all situation except for the ones just mentioned
                    if not isinstance(self.if_else_stack[-1].IR, IR.LoopBlock):
                        if self.if_else_stack[-1].state == len(self.if_else_stack[-1].if_stmt.successors)-2:
                            self.environment = copy.deepcopy(
                                self.stored_environments[self.if_else_stack[-1].if_stmt.id])
                            logger.info("program pointer back (if) to [%s] %s, stack height %d" % (
                                self.if_else_stack[-1].if_stmt.id, self.if_else_stack[-1].if_stmt.mnemonic, len(self.environment.program_stack)))
                    else:
                        self.if_else_stack.pop()

                elif self.current_instruction.mnemonic == 'ENDLOOP':
                    assert len(self.if_else_stack) > 0

                    block = self.if_else_stack[-1].IR
                    if block.mode == 'TRUE' and len(block.else_instructions) > 0:
                        self.environment = copy.deepcopy(
                            self.stored_environments[block.statement_id])
                        logger.info("program pointer back (if) to [%s] %s, stack height %d" % (
                            block.statement_id, 'IF', len(self.environment.program_stack)))
                        self.current_instruction = block.else_instructions[0]

                    else:
                        self.if_else_stack.pop()
                        itr = 0
                        loopsize = 0
                        for inst in block.loop_instructions:
                            if inst.mnemonic == 'IF':
                                block.loop_ir.append(inst.If_Else_Block)
                                if itr < loopsize:
                                    loopsize += 1
                                itr += 1
                            else:
                                block.loop_ir.extend(self.bytecode2ir[inst.id])
                                if itr < block.loop_size:
                                    loopsize += len(self.bytecode2ir[inst.id])
                                itr += 1
                                # self.ignored_insts.add(inst)
                        block.loop_size = loopsize
                        for inst in block.else_instructions:
                            if inst.mnemonic == 'IF':
                                block.else_ir_append(inst.If_Else_Block)
                            else:
                                block.else_ir.extend(self.bytecode2ir[inst.id])
                                # self.ignored_insts.add(inst)

                        if len(self.if_else_stack) > 0 and self.current_instruction.if_block_layer == None:
                            nested_block = self.if_else_stack[-1].IR
                            if isinstance(nested_block, IR.IfElseBlock):
                                if nested_block.mode == 'ELSE':
                                    nested_block.else_instructions.append(
                                        self.current_instruction.loop_stmt)
                                else:
                                    nested_block.if_instructions.append(
                                        self.current_instruction.loop_stmt)
                            elif isinstance(nested_block, IR.LoopBlock):
                                pass

                        self.current_instruction = self.current_instruction.successors[0]

                else:
                    self.current_instruction = self.current_instruction.successors[0]

            # multiple succs, store the alternate succ for later
            elif len(self.current_instruction.successors) > 1:
                if self.current_instruction.mnemonic == 'IF':
                    old_state = self.if_else_stack[-1].state
                    logger.info("traverse new branch old_state %d [%s] %s" % (
                        old_state, self.current_instruction.id, self.current_instruction.mnemonic))

                    # I move this block to here,since when 'alts_count == self.if_else_stack[-1].state',
                    # the pointer is not at 'EIF',but 'IF'(last time) instead,so the previous will never pop
                    # the self.if_else_stack,and also will never append the IR code for IF_ELSE blocks.
                    if old_state == len(self.current_instruction.successors):
                        assert len(self.if_else_stack) > 0
                        # check that we've executed all branches
                        alts_count = 2 if self.if_else_stack[-1].IR.mode == 'ELSE' else 1
                        logger.info("alts_count %d state %d" %
                                    (alts_count, self.if_else_stack[-1].state))
                        if self.if_else_stack[-1].state-1 == alts_count:
                            s = self.if_else_stack.pop()
                            block = s.IR
                            for inst in block.if_instructions:
                                # only append inst which is not in ignored list, (for remove the unnecessary jump instructions)
                                if not inst in self.ignored_insts:
                                    # An IF instruction should not be in the ignored list
                                    # or the whole If_Else_Block will not show up in the intermediate code
                                    if inst.mnemonic == 'IF':
                                        if(inst.id != s.if_stmt.id):
                                            block.if_branch.append(
                                                inst.If_Else_Block)
                                    elif inst.mnemonic == 'LOOP':
                                        block.if_branch.append(inst.LOOP_BLOCK)
                                    else:
                                        block.if_branch.extend(
                                            self.bytecode2ir[inst.id])
                                    if inst.id != s.if_stmt.id:
                                        self.ignored_insts.add(inst)

                            for inst in block.else_instructions:
                                # only append inst which is not in ignored list, (for remove the unnecessary jump instructions)
                                if not inst in self.ignored_insts:
                                    if inst.mnemonic == 'IF':
                                        block.else_branch.append(
                                            inst.If_Else_Block)
                                    elif inst.mnemonic == 'LOOP':
                                        block.else_branch.append(
                                            inst.LOOP_BLOCK)
                                    else:
                                        block.else_branch.extend(
                                            self.bytecode2ir[inst.id])
                                    self.ignored_insts.add(inst)

                            block.if_instructions = []
                            block.else_instructions = []
                            ir = [block]
                            # when poping off an if-else-block from the stack, if this is a nested one
                            # append its IR to the parent if/else block
                            if len(self.if_else_stack) > 0 and self.current_instruction.if_block_layer == None:
                                nested_block = self.if_else_stack[-1].IR
                                if nested_block.mode == 'ELSE':
                                    nested_block.else_instructions.append(
                                        self.current_instruction)
                                else:
                                    nested_block.if_instructions.append(
                                        self.current_instruction)
                        # add this in order to make the program keep going when quiting IF block and the whole IF
                        # _ELSE block
                        self.current_instruction = self.current_instruction.successors[
                            old_state-1].successors[0]

                    else:
                        self.current_instruction = self.current_instruction.successors[old_state]
                        self.if_else_stack[-1].state = old_state + 1
                else:
                    # is a JMPR/JROx, go to normal succ [0], breadcrumbs take care of [1].
                    self.current_instruction = self.current_instruction.successors[0]
            # ok, no succs
            else:
                assert len(self.current_instruction.successors) == 0
                # reached end of function, but we're still in a call
                # ie handle RETURN
                if len(self.call_stack) > 0:
                    while True:
                        self.execute_RETURN(tag)
                        if len(self.call_stack) == 0 or self.current_instruction:
                            break
                # ok, we really are all done here!
                else:
                    logger.info("leftovers if_else.env %d" %
                                len(self.if_else_stack))
                    if len(self.if_else_stack) > 0:
                        s = self.if_else_stack.pop()
                        block = s.IR
                        for inst in block.if_instructions:
                            # only append inst which is not in ignored list, (for remove the unnecessary jump instructions)
                            if not inst in self.ignored_insts:
                                # An IF instruction should not be in the ignored list
                                # or the whole If_Else_Block will not show up in the intermediate code
                                if inst.mnemonic == 'IF':
                                    if(inst.id != s.if_stmt.id):
                                        block.if_branch.append(
                                            inst.If_Else_Block)
                                elif inst.mnemonic == 'LOOP':
                                    block.if_branch.append(inst.LOOP_BLOCK)
                                else:
                                    block.if_branch.extend(
                                        self.bytecode2ir[inst.id])
                                    if inst.id != s.if_stmt.id:
                                        self.ignored_insts.add(inst)

                        for inst in block.else_instructions:
                            # only append inst which is not in ignored list, (for remove the unnecessary jump instructions)
                            if not inst in self.ignored_insts:
                                if inst.mnemonic == 'IF':
                                    block.else_branch.append(
                                        inst.If_Else_Block)
                                elif inst.mnemonic == 'LOOP':
                                    block.else_branch.append(inst.LOOP_BLOCK)
                                else:
                                    block.else_branch.extend(
                                        self.bytecode2ir[inst.id])
                                self.ignored_insts.add(inst)

                        block.if_instructions = []
                        block.else_instructions = []
                        ir = [block]
                        # when poping off an if-else-block from the stack, if this is a nested one
                        # append its IR to the parent if/else block
                        if len(self.if_else_stack) > 0 and self.current_instruction.if_block_layer == None:
                            nested_block = self.if_else_stack[-1].IR
                            if nested_block.mode == 'ELSE':
                                nested_block.else_instructions.append(
                                    self.current_instruction)
                            else:
                                nested_block.if_instructions.append(
                                    self.current_instruction)
                        # add this in order to make the program keep going when quiting IF block and the whole IF
                        # _ELSE block

                    assert len(self.if_else_stack) == 0
                    if not self.uncertain_callee_backup is None and self.current_instruction.id.startswith(tag):
                        #print 'this function works'
                        self.uncertain_callee_backup.possible_functions.append(
                            self.uncertain_callee_backup.function_itr)
                        self.environment = copy.deepcopy(
                            self.uncertain_callee_backup.backup_executor_status.environment)
                        self.if_else_stack = copy.deepcopy(
                            self.uncertain_callee_backup.backup_executor_status.if_else_stack)
                        for i in range(0, len(self.if_else_stack)):
                            self.if_else_stack[i].if_stmt.successors = self.uncertain_callee_backup.backup_executor_status.if_else_stack[i].if_stmt.successors
                            self.if_else_stack[i].if_stmt.predecessor = self.uncertain_callee_backup.backup_executor_status.if_else_stack[i].if_stmt.predecessor

                        self.current_instruction = self.uncertain_callee_backup.backup_executor_status.current_instruction
                        self.maximum_stack_depth = self.uncertain_callee_backup.backup_executor_status.maximum_stack_depth
                        self.call_stack = copy.deepcopy(
                            self.uncertain_callee_backup.backup_executor_status.call_stack)
                        for i in range(0, len(self.uncertain_callee_backup.backup_executor_status.call_stack)):

                            new_if_else_stack = copy.deepcopy(
                                self.uncertain_callee_backup.backup_executor_status.call_stack[i][-4])

                            for j in range(0, len(new_if_else_stack)):
                                new_if_else_stack[j].if_stmt = self.uncertain_callee_backup.backup_executor_status.call_stack[i][-4][j].if_stmt

                            oldtuple = self.call_stack[i]
                            newtuple = (oldtuple[0], self.uncertain_callee_backup.backup_executor_status.call_stack[i][1], self.uncertain_callee_backup.backup_executor_status.call_stack[i]
                                        [2], oldtuple[3], oldtuple[4], oldtuple[5], new_if_else_stack, oldtuple[7], oldtuple[8], oldtuple[9])
                            self.call_stack[i] = newtuple

                        self.bytecode2ir = copy.deepcopy(
                            self.uncertain_callee_backup.backup_executor_status.bytecode2ir)
                        self.already_seen_insts = copy.deepcopy(
                            self.uncertain_callee_backup.backup_executor_status.already_seen_insts)
                        self.ignored_insts = copy.deepcopy(
                            self.uncertain_callee_backup.backup_executor_status.ignored_insts)
                        self.if_else_stack = copy.deepcopy(
                            self.uncertain_callee_backup.if_else_stack)
                        self.uncertain_callee_backup.function_itr += 1
                        continue

                    self.current_instruction = None

        # ok, finished executing tag, now let's lift all of the IR into intermediateCodes

        #intermediateCodes = self.graphics_state_initialization_code() if tag == 'prep' else []
        intermediateCodes = []

        for inst in program.body.instructions:
            if inst not in self.ignored_insts:
                if inst.mnemonic == "IF":
                    intermediateCodes.append(inst.If_Else_Block)
                elif inst.mnemonic == "LOOP":
                    intermediateCodes.append(inst.If_Else_Block)
                else:
                    intermediateCodes.extend(self.bytecode2ir[inst.id])
        self.bytecodeContainer.IRs[tag] = self.fixupDestsToIR(
            intermediateCodes)
        # erase_lines(self.row_to_erase)
        #row_to_erase = 0

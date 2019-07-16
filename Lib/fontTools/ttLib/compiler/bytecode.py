import sys
import ast
import token
import copy
from fontTools.ttLib.data import dataType


class Bytecode:
    def __init__(self):
        self.prep = []
        self.fpgm = {}
        self.glyf = {}

    def set_code(self, code, p_type, p_tag):
        if p_type == 'prep':
            self.prep = code
        elif p_type == 'fpgm':
            self.fpgm[p_tag] = code
        elif p_type == 'glyf':
            self.glyf[p_tag] = code


class BytecodeProducer:
    class variable:
        def __init__(self, k=None, v=None):
            self.key = k      # terminal expression (identifier type)
            self.value = v    # any expression (except assignment exp)
            self.alias = None

        def __eq__(self, other):
            if other.key.value == self.key.value:
                return True
            return False

        def __str__(self):
            return str(self.key.value) + ":=" + str(self.value)

    class statement:
        def __init__(self, instruction, *data):
            self.instruction = instruction
            self.data = list(data)

        def __str__(self):
            if self.instruction == "PUSH":
                if all([int(d.value) >= 0 and int(d.value) <= 255 for d in self.data]):
                    string = "PUSHB[ ]\n"
                else:
                    string = "PUSHW[ ]\n"
                for d in self.data:
                    string += '      ' + str(d.value)

            elif self.instruction == "SWAP":
                string = "SWAP[ ]"
            elif self.instruction == "COPY":
                string = "DUP[ ]"
            elif self.instruction == "ROLL":
                string = "ROLL[ ]"
            elif self.instruction == "CINDEX":
                string = "CINDEX[ ]"
            elif self.instruction == "MINDEX":
                string = "MINDEX[ ]"
            elif self.instruction == "MPPEM":
                string = "MPPEM[ ]"
            elif self.instruction == "MPS":
                string = "MPS[ ]"
            elif self.instruction == "readIndexedStorage":
                if self.data[0].storage == "cvt_table":
                    string = "RCVT[ ]"
                elif self.data[0].storage == "storage_area":
                    string = "RS[ ]"

                else:
                    string = "other type read indexed storage"
            elif self.instruction == "writeToIndexedStorage":
                if self.data[0].storage == "cvt_table":
                    if self.data[0].unit == 'F':
                        string = "WCVTF[ ]"
                    elif self.data[0].unit == 'P':
                        string = "WCVTP[ ]"
                elif self.data[0].storage == "storage_area":
                    string = "WS[ ]"
                else:
                    string = "other type write to indexed storage"

            elif self.instruction == "unary":
                string = {
                    "NEG": "NEG[ ]",
                    "not": "NOT[ ]",
                    "abs": "ABS[ ]",
                    "ceil": "CEILING[ ]",
                    "floor": "FLOOR[ ]"

                }.get(self.data[0])

            elif self.instruction == "binary":
                string = {
                    "+": "ADD[ ]",
                    "-": "SUB[ ]",
                    "*": "MUL[ ]",
                    "/": "DIV[ ]",
                    "AND": "AND[ ]",
                    "GT": "GT[ ]",
                    "LT": "LT[ ]",
                    "EQ": "EQ[ ]",
                    "LE": "LTEQ[ ]",
                    "GE": "GTEQ[ ]",
                    "NE": "NEQ[ ]",
                    "OR": "OR[ ]",
                    "max": "MAX[ ]",
                    "min": "MIN[ ]"
                }.get(self.data[0].op)

            elif self.instruction == "methodCall":
                string = {
                    "ROUND_10": "ROUND[10]",
                    "ROUND_00": "ROUND[00]",
                    "ROUND_01": "ROUND[01]",
                    "ROUND_11": "ROUND[11]",
                    "MSIRP": "MSIRP",
                    "AA": "AA[ ]",
                    "ALIGNPTS": "ALIGNPTS",
                    "ALIGNRP": "ALIGNRP[ ]",
                    "CALL": "CALL[ ]",
                    "LOOPCALL": "LOOPCALL[ ]",
                    "DELTA": "DELTA",
                    "GC": "GC",
                    "IP": "IP[ ]",
                    "IUP": "IUP",
                    "ISECT": "ISECT[ ]",
                    "FLIPRGON": "FLIPRGON[ ]",
                    "FLIPRGOFF": "FLIPRGOFF[ ]",
                    "MD": "MD",
                    "MDAP": "MDAP",
                    "MDRP": "MDRP",
                    "MIAP": "MIAP",
                    "MIRP": "MIRP",
                    "MSIRP": "MSIRP",
                    "ROFF": "ROFF[ ]",
                    "SCFS": "SCFS[ ]",
                    "SDB": "SDB[ ]",
                    "SDPVTL": "SDPVTL",
                    "SDS": "SDS[ ]",
                    "SFVFS": "SFVFS[ ]",
                    "SFVTL": "SFVTL",
                    "SFVTPV": "SFVTPV[ ]",
                    "SPVFS": "SPVFS[ ]",
                    "SPVTL": "SPVTL",
                    "SHC": "SHC",
                    "SHP": "SHP",
                    "SHPIX": "SHPIX[ ]",
                    "SHZ": "SHZ",
                    "SLOOP": "SLOOP[ ]",
                    "SMD": "SMD[ ]",
                    "GETINFO": "GETINFO[ ]"
                }.get(self.data[0].methodName)
                if string == "MSIRP":
                    string = string + '['+str(self.data[0].data)+']'
                if string == "DELTA":
                    string = string + self.data[0].data + '[ ]'
                if string == "GC":
                    string = string + "["+str(self.data[0].data)+"]"
                if string == "IUP":
                    string = string + "["+str(self.data[0].data)+"]"
                if string == "MD":
                    string = string + "["+str(self.data[0].data)+"]"
                if string == "MDAP":
                    string = string + "["+str(self.data[0].data)+"]"
                if string == "MDRP":
                    string = string + "["+str(self.data[0].data)+"]"
                if string == "MIAP":
                    string = string + "["+str(self.data[0].data)+"]"
                if string == "MIRP":
                    string = string + "["+str(self.data[0].data)+"]"
                if string == "MSIRP":
                    string = string + "["+str(self.data[0].data)+"]"
                if string == "SDPVTL":
                    string = string + "["+str(self.data[0].data)+"]"
                if string == "SFVTL":
                    string = string + "["+str(self.data[0].data)+"]"
                if string == "SHC":
                    string = string + "["+str(self.data[0].data)+"]"
                if string == "SHP":
                    string = string + "["+str(self.data[0].data)+"]"
                if string == "SHZ":
                    string = string + "["+str(self.data[0].data)+"]"
                if string == "SPVTL":
                    string = string + "["+str(self.data[0].data)+"]"
                if string == None:
                    if not self.data[0].methodName is None:
                        string = "other methodCall:"+self.data[0].methodName
                    else:
                        string = "other methodCall:None"

            elif self.instruction == "RoundState_DTG":
                string = "RDTG[ ]"
            elif self.instruction == "RoundState_DG":
                string = "RTDG[ ]"
            elif self.instruction == "RoundState_G":
                string = "RTG[ ]"
            elif self.instruction == "RoundState_HG":
                string = "RTHG[ ]"
            elif self.instruction == "RoundState_UG":
                string = "RUTG[ ]"
            elif self.instruction == "RoundState_Super":
                string = "SROUND[ ]"

            elif self.instruction == "IF":
                string = "IF[ ]"
            elif self.instruction == "ELSE":
                string = "ELSE[ ]"
            elif self.instruction == "EIF":
                string = "EIF[ ]"

            elif self.instruction == "POP":
                string = "POP[ ]"
            elif self.instruction == "SVTCA":
                if self.data[0] == 0:
                    string = "SVTCA[0]"
                else:
                    string = "SVTCA[1]"
            elif self.instruction == "AUTOFLIP":
                if self.data[0].value == "true":
                    string = "FLIPON[ ]"
                else:
                    string = "FLIPOFF[ ]"
            elif self.instruction == "GFV":
                string = "GFV[ ]"
            elif self.instruction == "GPV":
                string = "GPV[ ]"

            elif self.instruction == "INSTCTRL":
                string = "INSTCTRL[ ]"
            elif self.instruction == "SCANCTRL":
                string = "SCANCTRL[ ]"
            elif self.instruction == "SCANTYPE":
                string = "SCANTYPE[ ]"
            elif self.instruction == "SCVTCI":
                string = "SCVTCI[ ]"
            elif self.instruction == "JMPR":
                string = "JMPR[ ]"
            elif self.instruction == "SFVTCA":
                string = "SFVTCA["+str(self.data[0].value)+"]"
            elif self.instruction == "SPVTCA":
                string = "SPVTCA["+str(self.data[0].value)+"]"
            elif self.instruction == "SRP":
                if self.data[0].value == "rp0":
                    string = "SRP0[ ]"
                elif self.data[0].value == "rp1":
                    string = "SRP1[ ]"
                else:
                    string = "SRP2[ ]"
            elif self.instruction == "SZP":
                if self.data[0].value == "zp0":
                    if self.data[0].is_all:
                        string = "SZPS[ ]"
                    else:
                        string = "SZP0[ ]"
                elif self.data[0].value == "zp1":
                    string = "SZP1[ ]"
                else:
                    string = "SZP2[ ]"
            elif self.instruction == "SSW":
                string = "SSW[ ]"
            else:
                string = self.instruction

            return string

    def __init__(self):
        self.variable_stack = None
        self.program = None
        self.function = None
        self.code = Bytecode()

    def get_bytecode(self):
        return self.code

    # check if this operation is a ROLL by checking current and next 3 expressions and matching pattern
    def is_ROLL_operation(self, current, next1, next2, next3):
        if not (isinstance(next1, ast.assignment_expression) and isinstance(next2, ast.assignment_expression) and isinstance(next3, ast.assignment_expression)):
            return False
        if not (isinstance(next1.left_oprand, ast.terminal_expression) and isinstance(next2.left_oprand, ast.terminal_expression) and isinstance(next3.left_oprand, ast.terminal_expression)):
            return False
        if not (isinstance(next1.right_oprand, ast.terminal_expression) and isinstance(next2.right_oprand, ast.terminal_expression) and isinstance(next3.right_oprand, ast.terminal_expression)):
            return False
        if not (next1.right_oprand.type == "identifier" and next2.right_oprand.type == "identifier" and next3.right_oprand.type == "identifier"):
            return False

        l0 = current.left_oprand.value
        l1 = next1.left_oprand.value
        l2 = next2.left_oprand.value
        l3 = next3.left_oprand.value

        r0 = current.right_oprand.value
        r1 = next1.right_oprand.value
        r2 = next2.right_oprand.value
        r3 = next3.right_oprand.value
        if l0 == r3 and l1 == r0 and l2 == r1 and l3 == r2:
            return True
        return False

    # check if this operation is a SWAP by checking current and next 2 expressions and matching pattern
    def is_SWAP_operation(self, current, next1, next2):
        if not (isinstance(next1, ast.assignment_expression) and isinstance(next2, ast.assignment_expression)):
            return False
        if not (isinstance(next1.left_oprand, ast.terminal_expression) and isinstance(next2.left_oprand, ast.terminal_expression)):
            return False
        if not (isinstance(next1.right_oprand, ast.terminal_expression) and isinstance(next2.right_oprand, ast.terminal_expression)):
            return False
        if not(next1.right_oprand.type == "identifier" and next2.right_oprand.type == "identifier"):
            return False

        l0 = current.left_oprand.value
        l1 = next1.left_oprand.value
        l2 = next2.left_oprand.value

        r0 = current.right_oprand.value
        r1 = next1.right_oprand.value
        r2 = next2.right_oprand.value
        if l0 == r2 and l1 == r0 and l2 == r1:
            return True

        return False

    def is_CINDEX_operation(self, exp):
        if len(self.variable_stack) < 1:
            return False
        if not isinstance(self.variable_stack[-1].value, ast.terminal_expression):
            return False
        if not self.variable_stack[-1].value.type == "int":
            return False
        index = self.variable_stack[-1].value.value

        if len(self.variable_stack) < index+1:
            return False

        if not exp.left_oprand.value == self.variable_stack[-1].key.value:
            return False

        if not isinstance(exp.right_oprand, ast.terminal_expression):
            return False

        if not exp.right_oprand.type == "identifier":
            return False

        if not exp.right_oprand.value == self.variable_stack[-index-1].key.value:
            return False

        return True

    def is_MINDEX_operation(self, exp, expressions, current_itr):
        # this is done by testing step by step, it is not a MINDEX if anyone step of test fails
        # 1. check if the first exp is 'identifier' := 'identifier'
        if not isinstance(exp.right_oprand, ast.terminal_expression):
            return 0
        if not exp.right_oprand.type == 'identifier':
            return 0

        # 2. check if the first exp is 'variable_stack[-1].key := variable_stack[-2].key'
        if len(self.variable_stack) < 2:
            return 0
        if (not self.variable(exp.left_oprand, None) == self.variable_stack[-1]) or (not self.variable(exp.right_oprand, None) == self.variable_stack[-2]):
            return 0

        # 3. check if the second exp is 'identifier' := 'identifier'
        itr = current_itr + 1
        if len(expressions) < itr + 1:
            return 0
        next_exp = expressions[itr]
        if not isinstance(next_exp, ast.assignment_expression):
            return 0
        if (not isinstance(next_exp.left_oprand, ast.terminal_expression)) or (not isinstance(next_exp.right_oprand, ast.terminal_expression)):
            return 0
        if (not next_exp.left_oprand.type == 'identifier') or (not next_exp.right_oprand.type == 'identifier'):
            return 0

        # 4. check if the second exp is 'variable_stack[-2].key := variable_stack[-ind].key', get ind if it is
        if not self.variable(next_exp.left_oprand, None) == self.variable_stack[-2]:
            return 0
        if not self.variable(next_exp.right_oprand, None) in self.variable_stack:
            return 0
        ind = self.variable_stack.index(
            self.variable(next_exp.right_oprand, None))
        ind = len(self.variable_stack) - ind

        if len(expressions) < itr + ind - 1 or len(self.variable_stack) < ind:
            return 0
        # 5. for each i from ind-2 -> 1
        # check if the next exp is 'variable_stack[len(variable_stack)-i+1].key := variable_stack[len(variable_stack)-i+2].key'
        for i in range(ind-2, 1, -1):
            itr += 1
            next_exp = expressions[itr]
            if not isinstance(next_exp, ast.assignment_expression):
                return 0
            if (not isinstance(next_exp.left_oprand, ast.terminal_expression)) or (not isinstance(next_exp.right_oprand, ast.terminal_expression)):
                return 0
            if (not next_exp.left_oprand.type == 'identifier') or (not next_exp.right_oprand.type == 'identifier'):
                return 0

            if (not self.variable(next_exp.left_oprand, None) in self.variable_stack) or (not self.variable(next_exp.right_oprand, None) in self.variable_stack):
                return 0

            ind1 = self.variable_stack.index(
                self.variable(next_exp.left_oprand, None))
            ind2 = self.variable_stack.index(
                self.variable(next_exp.right_oprand, None))
            if (not ind1 == len(self.variable_stack)-i-1) or (not ind2 == len(self.variable_stack)-i):
                return 0
        # 6. check if the last one is 'variable_stack[-ind].key := variable_stack[-1].key'
        itr += 1
        next_exp = expressions[itr]
        if not isinstance(next_exp, ast.assignment_expression):
            return 0
        if (not isinstance(next_exp.left_oprand, ast.terminal_expression)) or (not isinstance(next_exp.right_oprand, ast.terminal_expression)):
            return 0
        if (not next_exp.left_oprand.type == 'identifier') or (not next_exp.right_oprand.type == 'identifier'):
            return 0
        if (not self.variable(next_exp.left_oprand, None) == self.variable_stack[-ind]) or (not self.variable(next_exp.right_oprand, None) == self.variable_stack[-1]):
            return 0

        # 7. return the index of MINDEX if all tests pass, return 0 otherwise wheneven the test fails at some step
        return ind-1

    def generate_code(self, func_AST):
        self.function = func_AST
        self.program = []
        self.variable_stack = []
        # push the function arguments into the variable stack (also change the variable name to local)
        if func_AST.arguments:
            for i in range(0, len(func_AST.arguments)):
                arg_name = "arg$"+str(len(func_AST.arguments)-i)
                splits = func_AST.arguments[-i-1].split('_')
                var_name = "$fpgm_"+str(func_AST.function_num)+"_"+splits[-1]
                next_arg_var = self.variable(ast.terminal_expression(
                    "identifier", var_name), ast.terminal_expression("identifier", arg_name))
                next_arg_var.alias = arg_name
                self.variable_stack.append(next_arg_var)

        expressions = func_AST.expressions
        self.process_expressions(expressions)

        # output bytecode (to screen)
        c = []
        if func_AST.function_type == "fpgm":
            c.append("PUSHB[ ]")
            c.append(str(func_AST.function_num))
            c.append("FDEF[ ]")
        for s in self.program:
            c.append(str(s))
        if func_AST.function_type == "fpgm":
            stack_effect_without_POP = len(self.variable_stack) - len(func_AST.arguments)
            # need extra POP[ ]s at the end
            for k in range(0, stack_effect_without_POP - func_AST.stack_effect):
                c.append("POP[ ]")
            c.append("ENDF[ ]")

            self.code.set_code(c, func_AST.function_type,
                               func_AST.function_num)
        elif func_AST.function_type == 'prep':
            self.code.set_code(c, func_AST.function_type, None)
        elif func_AST.function_type == 'glyf':
            self.code.set_code(c, func_AST.function_type,
                               func_AST.function_tag)

        self.program = []
        self.variable_stack = []

    def process_expressions(self, expressions):
        i = 0
        while i < len(expressions):
            exp = expressions[i]
            # if this is an assignment exp
            if isinstance(exp, ast.assignment_expression):
                # the left operand is a terminal expression
                if isinstance(exp.left_oprand, ast.terminal_expression):
                    if exp.left_oprand.type == "GS":
                        if exp.left_oprand.value.startswith("instruction_control"):
                            s = self.statement("INSTCTRL")
                            self.program.append(s)
                            self.variable_stack.pop()
                            self.variable_stack.pop()
                            i += 1
                            continue
                        if exp.left_oprand.value == "scan_control":
                            s = self.statement("SCANCTRL")
                            self.program.append(s)
                            self.variable_stack.pop()
                            i += 1
                            continue
                        if exp.left_oprand.value == "scan_type":
                            s = self.statement("SCANTYPE")
                            self.program.append(s)
                            self.variable_stack.pop()
                            i += 1
                            continue
                        if exp.left_oprand.value.startswith("rp"):
                            for k in range(0, exp.pops):
                                pop_stmt = self.statement("POP")
                                self.program.append(pop_stmt)
                                self.variable_stack.pop()
                            s = self.statement("SRP")
                            self.program.append(s)
                            self.variable_stack.pop()
                            s.data.append(exp.left_oprand)
                            i += 1
                            continue
                        if exp.left_oprand.value.startswith("zp"):
                            s = self.statement("SZP")
                            self.program.append(s)
                            self.variable_stack.pop()
                            s.data.append(exp.left_oprand)
                            if exp.left_oprand.is_all:
                                i += 3
                            else:
                                i += 1
                            continue
                        if exp.left_oprand.value == "single_width_cutin":
                            s = self.statement("SCVTCI")
                            self.program.append(s)
                            self.variable_stack.pop()
                            i += 1
                            continue
                        if exp.left_oprand.value == "single_width_value":
                            s = self.statement("SSW")
                            self.program.append(s)
                            self.variable_stack.pop()
                            i += 1
                            continue
                        if exp.left_oprand.value == "auto_flip":
                            s = self.statement("AUTOFLIP")
                            s.data.append(exp.right_oprand)
                            self.program.append(s)
                            i += 1
                            continue
                        if i+1 < len(expressions):
                            if isinstance(expressions[i+1], ast.assignment_expression):
                                if isinstance(expressions[i+1].left_oprand, ast.terminal_expression):
                                    if exp.left_oprand.value == "freedom_vector" and expressions[i+1].left_oprand.value == "projection_vector":
                                        s = self.statement("SVTCA")
                                        if exp.right_oprand.value == 0:
                                            s.data.append(0)
                                        else:
                                            s.data.append(1)
                                        self.program.append(s)
                                        i += 2
                                        continue
                        # if this fails the test above
                        if exp.left_oprand.value == "freedom_vector":
                            if isinstance(exp.right_oprand, ast.terminal_expression):
                                if exp.right_oprand.type == "int":
                                        # this is an SFVTCA[a] operation
                                    s = self.statement("SFVTCA", exp.right_oprand)
                                    self.program.append(s)
                                    i += 1
                                    continue

                        if exp.left_oprand.value == "projection_vector":
                            if isinstance(exp.right_oprand, ast.terminal_expression):
                                if exp.right_oprand.type == "int":
                                    # this is an SPVTCA[a] operation
                                    s = self.statement("SPVTCA", exp.right_oprand)
                                    self.program.append(s)
                                    i += 1
                                    continue

                    # if this variable is not in variable stack
                    if not self.variable(k=exp.left_oprand) in self.variable_stack:
                        if isinstance(exp.right_oprand, ast.terminal_expression):
                            if exp.right_oprand.type == "int":
                                # this is a simple constant assignment
                                v = self.variable(exp.left_oprand, exp.right_oprand)
                                self.variable_stack.append(v)
                                s = self.statement("PUSH", exp.right_oprand)
                                self.program.append(s)
                                i += 1
                                continue
                            elif exp.right_oprand.type == "MPPEM":
                                # this is an MPPEM operation
                                v = self.variable(exp.left_oprand, exp.right_oprand)
                                self.variable_stack.append(v)
                                s = self.statement("MPPEM", exp.right_oprand)
                                self.program.append(s)
                                i += 1
                                continue
                            elif exp.right_oprand.type == "PointSize":
                                # this is an MPS operation
                                v = self.variable(exp.left_oprand, exp.right_oprand)
                                self.variable_stack.append(v)
                                s = self.statement("MPS", exp.right_oprand)
                                self.program.append(s)
                                i += 1
                                continue

                            elif exp.right_oprand.type == "identifier":
                                # if the right side is an identifier, it could be copy/swap/roll instruction...

                                # 1. check if this is a roll,by checking the next 3 expressions
                                if len(expressions) > i+3 and len(self.variable_stack) > 2:
                                    next1 = expressions[i+1]
                                    next2 = expressions[i+2]
                                    next3 = expressions[i+3]
                                    if self.is_ROLL_operation(exp, next1, next2, next3):
                                            # this is a roll operation,roll the top 3 variables,roll the values of top 3 variables
                                        temp = self.variable_stack[-1].value
                                        exp.left_oprand.value
                                        self.variable_stack[-1].value = self.variable_stack[-3].value
                                        self.variable_stack[-3].value = self.variable_stack[-2].value
                                        self.variable_stack[-2].value = temp
                                        s = self.statement("ROLL")
                                        self.program.append(s)
                                        i = i + 3 + 1
                                        continue

                                # 2. check if this is a swap, by checking the next 2 expressions
                                if len(expressions) > i+2 and len(self.variable_stack) > 1:
                                    next1 = expressions[i+1]
                                    next2 = expressions[i+2]
                                    if self.is_SWAP_operation(exp, next1, next2):
                                        # this is a swap operation, swap the values of top 2 variables
                                        temp = self.variable_stack[-1].value
                                        self.variable_stack[-1].value = self.variable_stack[-2].value
                                        self.variable_stack[-2].value = temp
                                        s = self.statement("SWAP")
                                        self.program.append(s)
                                        i = i + 3
                                        continue

                                # 3. check if this is a copy (it fails 1, but pass 2, -> it's a copy)
                                if len(self.variable_stack) > 0:
                                    if exp.right_oprand.value == self.variable_stack[-1].key.value:
                                        s = self.statement("COPY")
                                        self.program.append(s)
                                        v = self.variable(exp.left_oprand, self.variable_stack[-1].value)
                                        self.variable_stack.append(v)
                                        i += 1
                                        continue
                            elif exp.right_oprand.type == "GS":
                                if exp.right_oprand.value == "freedom_vector_0":
                                    if isinstance(expressions[i+1], ast.assignment_expression):
                                        if isinstance(expressions[i+1].right_oprand, ast.terminal_expression):
                                            if expressions[i+1].right_oprand.type == "GS" and expressions[i+1].right_oprand.value == "freedom_vector_1":
                                                s = self.statement("GFV")
                                                s.data.append(exp)
                                                self.program.append(s)
                                                self.variable_stack.append(self.variable(
                                                    exp.left_oprand, "free_vector_0"))
                                                self.variable_stack.append(self.variable(
                                                    expressions[i+1].left_oprand, "free_vector_1"))
                                                i += 2
                                                continue
                                elif exp.right_oprand.value == "projection_vector_0":
                                    if isinstance(expressions[i+1], ast.assignment_expression):
                                        if isinstance(expressions[i+1].right_oprand, ast.terminal_expression):
                                            if expressions[i+1].right_oprand.type == "GS" and expressions[i+1].right_oprand.value == "projection_vector_1":
                                                s = self.statement("GPV")
                                                s.data.append(exp)
                                                self.program.append(s)
                                                self.variable_stack.append(self.variable(
                                                    exp.left_oprand, "projection_vector_0"))
                                                self.variable_stack.append(self.variable(
                                                    expressions[i+1].left_oprand, "projection_vector_1"))
                                                i += 2
                                                ne = expressions[i]
                                                continue

                        else:
                            if isinstance(exp.right_oprand, ast.roundState_expression):
                                s = self.statement(exp.right_oprand.type)
                                self.program.append(s)
                                if exp.right_oprand.type in ["RoundState_Super", "RoundState_45"]:
                                    self.variable_stack.pop()
                                i += 1
                                continue
                            elif isinstance(exp.right_oprand, ast.methodCall_expression):
                                if exp.right_oprand.methodName == "GC":
                                    s = self.statement("methodCall", exp.right_oprand)
                                    self.program.append(s)
                                    self.variable_stack[-1].value = dataType.AbstractValue()

                    # this is assignment exp->left oprand is terminal(identifier)->identifier is in variable stack
                    else:
                        if self.is_MINDEX_operation(exp, expressions, i) > 0:
                            skip = self.is_MINDEX_operation(
                                exp, expressions, i)
                            self.variable_stack[-1].value = self.variable_stack[-skip-1].value
                            for k in range(skip, 0, -1):
                                self.variable_stack[-k -
                                                    1].value = self.variable_stack[-k].value
                            self.variable_stack.pop()

                            s = self.statement("MINDEX")
                            self.program.append(s)
                            i += skip+1
                            continue

                        if self.is_CINDEX_operation(exp):
                            index = self.variable_stack[-1].value.value
                            self.variable_stack[-1].value = self.variable_stack[-index-1].value
                            s = self.statement("CINDEX")
                            self.program.append(s)
                            i += 1
                            continue
                        elif isinstance(exp.right_oprand, ast.IndexedStorage_expression):
                            if len(self.variable_stack) > 0:
                                if self.variable_stack[-1].key.value == exp.left_oprand.value:
                                    s = self.statement("readIndexedStorage", exp.right_oprand)
                                    self.program.append(s)
                                    self.variable_stack[-1].value = exp.right_oprand
                                    i += 1
                                    continue
                        elif isinstance(exp.right_oprand, ast.binary_expression):
                            self.variable_stack.pop()
                            self.variable_stack[-1].value = exp.right_oprand
                            s = self.statement("binary", exp.right_oprand)
                            self.program.append(s)
                            i += 1
                            continue

                        elif isinstance(exp.right_oprand, ast.unary_expression):
                            if len(self.variable_stack) > 0:
                                if self.variable_stack[-1].key.value == exp.left_oprand.value:
                                    s = self.statement("unary", exp.right_oprand.op)
                                    self.program.append(s)
                                    self.variable_stack[-1].value = exp.right_oprand
                                    i += 1
                                    continue
                        elif isinstance(exp.right_oprand, ast.methodCall_expression):
                            s = self.statement("methodCall", exp.right_oprand)
                            self.variable_stack[-1].value = exp.right_oprand
                            self.program.append(s)
                            i += 1
                            continue
                        else:
                            # if the variable is in the stack and nothing above is satisfied
                            # it is regarded that there are pop operations before here
                            temp_var = self.variable(exp.left_oprand, None)
                            index = len(self.variable_stack) - \
                                self.variable_stack.index(temp_var)
                            for itr in range(0, index):
                                s = self.statement("POP")
                                self.program.append(s)
                                self.variable_stack.pop()
                            continue

                # the left operand is an indexed storage location
                elif isinstance(exp.left_oprand, ast.IndexedStorage_expression):
                    if isinstance(exp.right_oprand, ast.terminal_expression):
                        if (self.variable_stack) > 1:
                            self.variable_stack.pop()
                            self.variable_stack.pop()
                            s = self.statement("writeToIndexedStorage", exp.left_oprand)
                            self.program.append(s)
                            i += 1
                            continue
            
            elif isinstance(exp, ast.loop_expression):
                # rewrite this loop as an IF with an unconditional jump
                if_stmt = self.statement('IF')
                self.program.append(if_stmt)
                self.variable_stack.pop()
                loop_body = exp.loop_branch[0:exp.loop_size]
                stack_len_before_loop = len(self.variable_stack)

                self.process_expressions(loop_body)

                stack_len_after_loop = len(self.variable_stack)
                jmpr_stmt = self.statement('JMPR')
                eif_stmt = self.statement('EIF')
                self.program.append(jmpr_stmt)
                self.program.append(eif_stmt)
                # TODO: I'm not sure if this needs to be here. 
                self.variable_stack.pop()

                for k in range(0, stack_len_after_loop-stack_len_before_loop):
                    pop_stmt = self.statement('POP')
                    self.program.append(pop_stmt)

            if isinstance(exp, ast.if_expression):
                # declare variable stack backup variables
                var_stack_after_if_branch = None
                var_stack_after_else_branch = None
                var_stack_backup = None

                # push if instruction, pop a variable from variable_stack
                if_stmt = self.statement("IF")
                self.program.append(if_stmt)
                self.variable_stack.pop()

                # deepcopy current variable stack to var_stack_backup
                var_stack_backup = copy.deepcopy(self.variable_stack)

                # process if branch
                self.process_expressions(exp.if_branch)

                # deepcopy current variable stack to var_stack_after_if_branch
                var_stack_after_if_branch = copy.deepcopy(
                    self.variable_stack)

                # if else branch is not empty
                if len(exp.else_branch) > 0:
                    # push else statement
                    else_stmt = self.statement("ELSE")
                    self.program.append(else_stmt)
                    # remember the position (index) of the else statement, in case pops are necessary
                    else_stmt_index = len(self.program)-1
                    # restore the variable stack and process the else branch
                    self.variable_stack = copy.deepcopy(var_stack_backup)
                    self.process_expressions(exp.else_branch)
                    # deepcopy current variable stack to var_stack_after_else_branch
                    var_stack_after_else_branch = copy.deepcopy(
                        self.variable_stack)

                    # configure pop instructions at the end of if/else branches
                    #  if else branch has more variables, need pops at the end of else branch
                    if len(var_stack_after_else_branch) > len(var_stack_after_if_branch):
                        num_to_pop = len(
                            var_stack_after_else_branch) - len(var_stack_after_if_branch)
                        for k in range(0, num_to_pop):
                            # append pop statment at the end of program and pop a variable from else_branch
                            pop_stmt = self.statement("POP")
                            self.program.append(pop_stmt)
                            var_stack_after_else_branch.pop()

                    #  if if branch has more variables, need pops at the end of if branch
                    elif len(var_stack_after_if_branch) > len(var_stack_after_else_branch):
                        num_to_pop = len(
                            var_stack_after_if_branch) - len(var_stack_after_else_branch)
                        pos = else_stmt_index
                        for k in range(0, num_to_pop):
                            # insert pop statement to the index of else statement
                            pop_stmt = self.statement("POP")
                            self.program.insert(pos, pop_stmt)
                            pos += 1
                            # pop a variable from if branch
                            var_stack_after_if_branch.pop()

                    # append eif statement
                    eif_stmt = self.statement("EIF")
                    self.program.append(eif_stmt)
                    # set current variable stack to var_stack_after_else_branch (or var_stack_after_if_branch)
                    self.variable_stack = var_stack_after_else_branch

                # if else branch is empty, var stack after "else branch" is backup var stack
                else:
                    # if the if branch reduced the variable stack size, need else branch with pops
                    if len(var_stack_backup) > len(var_stack_after_if_branch):
                        num_to_pop = len(var_stack_backup) - \
                            len(var_stack_after_if_branch)
                        # append else statement
                        else_stmt = self.statement("ELSE")
                        self.program.append(else_stmt)
                        for k in range(0, num_to_pop):
                            # append pop statement, and pop a variable from var_stack_backup
                            pop_stmt = self.statement("POP")
                            self.program.append(pop_stmt)
                            var_stack_backup.pop()

                    # if the if branch increased the variable stack size, need pops at the end of the if branch
                    elif len(var_stack_after_if_branch) > len(var_stack_backup):
                        num_to_pop = len(
                            var_stack_after_if_branch) - len(var_stack_backup)
                        for k in range(0, num_to_pop):
                            # append pop to the end and pop a variable from var_stack_after_if_branch
                            pop_stmt = self.statement("POP")
                            self.program.append(pop_stmt)
                            var_stack_after_if_branch.pop()

                    # append eif statement
                    eif_stmt = self.statement("EIF")
                    self.program.append(eif_stmt)
                    # set the current variable stack to var_stack_backup (or var_stack_after_if_branch)
                    self.variable_stack = var_stack_backup

                # increment program pointer and continue
                i += 1
                continue

            elif isinstance(exp, ast.methodCall_expression):
                s = self.statement("methodCall", exp)
                self.program.append(s)
                if exp.methodName == "MSIRP":
                    self.variable_stack.pop()
                    self.variable_stack.pop()

                elif exp.methodName == "ALIGNRP":
                    for k in range(0, exp.data):
                        self.variable_stack.pop()

                elif exp.methodName == "CALL" or exp.methodName == "LOOPCALL":
                    # pop callee var
                    self.variable_stack.pop()
                    if exp.methodName == "LOOPCALL":
                        self.variable_stack.pop()
                    # configure stack effect
                    repeats = 1
                    if exp.methodName == "LOOPCALL":
                        repeats = exp.repeats
                    if exp.stack_effect < 0:
                        for k in range(0, -exp.stack_effect*repeats):
                            self.variable_stack.pop()
                    elif exp.stack_effect > 0:
                        tag = '$'
                        if len(self.variable_stack) == 0:
                            if not self.function.function_type == 'fpgm':
                                if self.function.function_tag == None:
                                    tag = tag+'prep_'
                                else:
                                    tag = tag+self.function.function_tag+'_'

                            else:
                                tag += 'fpgm_'
                        else:
                            tag = self.variable_stack[-1].key.value.split('_')[
                                0]

                            if self.function.function_type == "fpgm":
                                tag = tag + '_' + \
                                    str(self.function.function_num) + '_'
                            else:
                                tag = tag + '_'

                        for k in range(0, exp.stack_effect*repeats):
                            var_key_str = tag + \
                                str(len(self.variable_stack)+1)
                            var_val_str = '$arg_' + str(k+1)
                            var = self.variable(ast.terminal_expression(
                                "identifier", var_key_str), ast.terminal_expression("identifier", var_val_str))
                            self.variable_stack.append(var)

                elif exp.methodName == "AA":
                    self.variable_stack.pop()
                elif exp.methodName == "ALIGNPTS":
                    self.variable_stack.pop()
                    self.variable_stack.pop()
                elif exp.methodName == "DELTA":
                    self.variable_stack.pop()
                    for k in range(0, len(exp.args)):
                        self.variable_stack.pop()
                elif exp.methodName == "IP":
                    for k in range(0, len(exp.args)):
                        self.variable_stack.pop()
                elif exp.methodName == "MD":
                    self.variable_stack.pop()
                    self.variable_stack[-1].value = dataType.Distance()
                elif exp.methodName == "MDAP":
                    self.variable_stack.pop()
                elif exp.methodName == "MDRP":
                    self.variable_stack.pop()
                elif exp.methodName == "MIAP":
                    self.variable_stack.pop()
                    self.variable_stack.pop()
                elif exp.methodName == "MIRP":
                    self.variable_stack.pop()
                    self.variable_stack.pop()
                elif exp.methodName == "MSIRP":
                    self.variable_stack.pop()
                    self.variable_stack.pop()
                elif exp.methodName == "SCFS":
                    self.variable_stack.pop()
                    self.variable_stack.pop()
                elif exp.methodName == "SDB":
                    self.variable_stack.pop()
                elif exp.methodName == "SDPVTL":
                    self.variable_stack.pop()
                    self.variable_stack.pop()
                elif exp.methodName == "SDS":
                    self.variable_stack.pop()
                elif exp.methodName == "SFVFS":
                    self.variable_stack.pop()
                    self.variable_stack.pop()
                elif exp.methodName == "SPVFS":
                    self.variable_stack.pop()
                    self.variable_stack.pop()
                elif exp.methodName == "SFVTL":
                    self.variable_stack.pop()
                    self.variable_stack.pop()
                elif exp.methodName == "SPVTL":
                    self.variable_stack.pop()
                    self.variable_stack.pop()
                elif exp.methodName == "SHC":
                    self.variable_stack.pop()
                elif exp.methodName == "SHP":
                    for k in range(0, len(exp.args)):
                        self.variable_stack.pop()
                elif exp.methodName == "SHPIX":
                    for k in range(0, exp.pops):
                        pop_stmt = self.statement("POP")
                        self.program.insert(len(self.program)-1, pop_stmt)
                        self.variable_stack.pop()
                    self.variable_stack.pop()
                    self.variable_stack.pop()
                elif exp.methodName == "SHZ":
                    self.variable_stack.pop()
                elif exp.methodName == "SLOOP":
                    self.variable_stack.pop()
                elif exp.methodName == "SMD":
                    self.variable_stack.pop()
                elif exp.methodName == "FLIPRGON" or exp.methodName == "FLIPRGOFF":
                    self.variable_stack.pop()
                    self.variable_stack.pop()
                elif exp.methodName == "ISECT":
                    for k in range(0, 5):
                        self.variable_stack.pop()

                i += 1
                continue
            # TODO should we throw if we reach here? code did not match any of the above cases.
            i += 1

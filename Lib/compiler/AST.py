import token
import os
import sys


class font_AST:
    def __init__(self):
	self.font_name = None
	self.output_dir = None

        self.prep_function = None
        self.program_functions = []
        self.glyph_functions = []
	self.fpgm2args = {}
	self.fpgm2stack_effect = {}

    def add_fpgm_args(self,callee,args,stack_effect):
        self.fpgm2args[callee] = args
	self.fpgm2stack_effect[callee] = stack_effect

    def find_ast_by_tag(self,tag):
        if tag == "prep":
            return self.prep_function

        for t in self.glyph_functions:
            if t.function_tag == tag:
                return t
        return None

    def find_ast_by_fpgm_num(num):
        for t in self.program_functions:
            if t.num == num:
                return t
        return None

# a function instance is the root of a AST
# it contains a list of expressions
class function:
    def __init__(self):
        # 3 types of functions, prep glyf fpgm
        self.function_type = None
        self.function_num = None
        self.function_tag = None
	self.font_ast = None
        self.expressions = []
        self.branch_stack = []
        self.arguments = []
        self.stack_effect = 0

    def push_expression(self,exp):
        if len(self.branch_stack) == 0:
            self.expressions.append(exp)
        else:
            top_branch = self.branch_stack[-1]
            if isinstance(top_branch,if_expression):
                if top_branch.status == "IF":
                    top_branch.if_branch.append(exp)
                else:
                    top_branch.else_branch.append(exp)
            elif isinstance(top_branch,loop_expression):
                top_branch.loop_branch.append(exp)


# expressions are building block of blocks, it is a parent class
class expression:
    def __init__(self):
        self.type = None


# these are the basic expressions
class terminal_expression(expression):
    def __init__(self,t=None,v=None):
        expression.__init__(self)
        self.type = t
        self.value = v
	self.is_all = False
    def __str__(self):
        return "terminal expression: type="+str(self.type)+" value="+str(self.value)     

class comparison_expression(expression):
    def __init__(self):
        expression.__init__(self)
        self.op = None
        self.left_oprand = None
        self.right_oprand = None


class binary_expression(expression):
    def __init__(self):
        self.op = None
        self.oprand1 = None
        self.oprand2 = None
        self.result = None
    def __str__(self):
        return "binary expression: operator="+str(self.op)+" oprand1=("+str(self.oprand1)+")"+" oprand2=("+str(self.oprand2)+")"


class methodCall_expression(expression):
    def __init__(self,method=None,data=None,args=None,pops=0):
        self.methodName = method
	self.data = data
	self.args = args
	self.pops = pops
    def __str__(self):
	return "method call expression: method="+str(self.methodName)

class call_expression(methodCall_expression):
    def __init__(self,callee,stack_effect,args):
	self.methodName = "CALL"
	self.data = None
	self.args = args
	self.callee = callee
	self.stack_effect = stack_effect
class loopcall_expression(methodCall_expression):
    def __init__(self,callee,repeats,stack_effect,args):
        self.methodName = "LOOPCALL"
	self.data = None
	self.args = args
	self.callee = callee
	self.stack_effect = stack_effect
	self.repeats = repeats

class unary_expression(expression):
    def __init__(self):
        self.op = None
        self.oprand = None
    def __str__(self):
        return "unary expression: operator="+str(self.op)+" oprand=("+str(self.oprand)+")"



class if_expression(expression):
    def __init__(self):
        self.mode = "IF"
        self.status = "IF"
	self.reverse = False
        self.condition_expression = None
        self.if_branch = []
        self.else_branch = []
        self.parent = None
	self.variable_stack_len_before_if = 0
	self.variable_stack_len_before_else = 0
	self.variable_stack_len_before_eif = 0

    def __str__(self):
        return "if expression:"

class loop_expression(expression):
    def __init__(self):
        self.condition_expression = None
        self.loop_branch = []
        self.parent = None
	self.loop_size = 0
    def __str__(self):
        return "loop expression"

class assignment_expression(expression):
    def __init__(self):
        expression.__init__(self)
        self.left_oprand = None
        self.right_oprand = None
	self.pops = 0
    def __str__(self):
        return "assignment expression: left_oprand="+str(self.left_oprand)+" right_oprand="+str(self.right_oprand)



class IndexedStorage_expression(expression):
    def __init__(self):
        self.storage = None
	self.index = None
	self.unit = None
	self.index_type = None  # index type could be identifier/int

    def __str__(self):
	return "IndexedStorage expression : %s[%s]" % (self.storage, self.index)


class roundState_expression(expression):
    def __init__(self,t,d=None):
        self.type = t
        self.data = d
        


# if else block is a subclass of expression,which contains a condition expression
# a if-block of expressions and else-block of expressions
class if_else_block(expression):
    def __init__(self):
        expression.__init__(self)
        self.condition = None
        self.if_block = None
        self.else_block = None

# while block is a subclass of expression,which contains a condition expression
# and a loop-block of expressions
class while_block(expression):
    def __init__(self):
        expression.__init__(self)
        self.condition = None
        self.loop_block = None


def get_exp(tokens):

    # return None for empty expression
    if len(tokens) == 0:
        return None

    # return terminal expression, terminal expressions can be identifiers(variables) and constants(int/float/(bool?))
    if len(tokens) == 1:
        if isinstance(tokens[0],token.constant) or isinstance(tokens[0],token.identifier):
            exp = terminal_expression(tokens[0])
            exp.type = "TERMINAL"
            return exp

    # return assignment expression
    if len(tokens) > 2:
        if isinstance(tokens[1],token.operator) and tokens[1].value == "ASSIGNMENT":
            exp = assignment_expression()
            exp.type = "ASSIGNMENT"
            exp.left_oprand = get_exp([tokens[0]])
            exp.right_oprand = get_exp(tokens[2:])
            return exp        

    # return comparison expression
    if len(tokens) > 2:
        position = -1
        for i in range(0,len(tokens)):
            t = tokens[i]
            if isinstance(t,token.operator) and t.value in ["GT","EQ"]:
                if position > -1:
                    assert(False)
                else:
                    position = i

        left = [0,i-1]
        right = [i+1,]
        exp = comparison_expression()
        exp.op = t.value
        exp.left_oprand = get_exp(left)
        exp.right_oprand = get_exp(right)
        exp.type = "COMPARISON"
        return exp
                           






# return a AST root of the a block of tokens (function/expression block)
def construct_AST(tokens_list):
    root = function()
    for i in range(0,len(tokens_list)):
        tokens = tokens_list[i]
        exp = get_exp(tokens)
        root.expressions.append(exp)



    return root






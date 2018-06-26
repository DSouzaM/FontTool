import sys
import AST
import token
import copy
from fontTools.ttLib.data import dataType

class Bytecode:
    def __init__(self):
        self.prep = []
        self.fpgm = {}
        self.glyf = {}

    def set_code(self,code,p_type,p_tag):
        if p_type == 'prep':
            self.prep = code
        if p_type == 'fpgm':
            self.fpgm[p_tag] = code
        if p_type == 'glyf':
            self.glyf[p_tag] = code




class bytecode_producer:
    class variable:
       # the left of a variable must be a trminal expression(identifier)
       # the right of a variable could be any expression except an assignment
       
        def __init__(self,k = None,v = None):
            self.key = k      # terminal expression(identifier type)
            self.value = v    # any expression (except assignment exp)
	    self.alias = None
        def __eq__(self,other):
             if other.key.value == self.key.value:
                 return True
             return False

        def __str__(self):
            return str(self.key.value) + ":=" + str(self.value)


    
    class statement:
        def __init__(self):
            self.instruction = None
            self.data = []

        def __str__(self):
            if self.instruction == "PUSH":
		if int(self.data[0].value) >=0 and int(self.data[0].value)<=255:
		    string = "PUSHB[ ]\n"
		else:
		    string = "PUSHW[ ]\n"
                for d in self.data:
                    string = string + '      ' + str(d.value)
           
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
		    string ="WS[ ]"
		else:
		    string ="other type write to indexed storage"

	    elif self.instruction == "unary":
		string = {
		    "NEG" : "NEG[ ]",
		    "not" : "NOT[ ]",
		    "abs" : "ABS[ ]",
		    "ceil": "CEILING[ ]",
		    "floor": "FLOOR[ ]"
	
		}.get(self.data[0])

	    elif self.instruction == "binary":
	        string = {
		    "+" : "ADD[ ]",
		    "-" : "SUB[ ]",
		    "*" : "MUL[ ]",
		    "/" : "DIV[ ]",
		    "AND" : "AND[ ]",
		    "GT"  : "GT[ ]",
		    "LT"  : "LT[ ]",
		    "EQ"  : "EQ[ ]",
	 	    "LE": "LTEQ[ ]",
		    "GE": "GTEQ[ ]",
		    "NE": "NEQ[ ]",
		    "OR" : "OR[ ]",
		    "max":"MAX[ ]",
		    "min":"MIN[ ]"
		         }.get(self.data[0].op)

	    elif self.instruction == "methodCall":
                string = {
	            "ROUND_10" : "ROUND[10]",
		    "ROUND_00" : "ROUND[00]",
		    "ROUND_01" : "ROUND[01]",
		    "ROUND_11" : "ROUND[11]",
		    "MSIRP" : "MSIRP",
		    "AA"  : "AA[ ]",
	 	    "ALIGNPTS":"ALIGNPTS",
		    "ALIGNRP": "ALIGNRP[ ]",
		    "CALL" : "CALL[ ]",
		    "LOOPCALL" : "LOOPCALL[ ]",
		    "DELTA": "DELTA",
		    "GC"   : "GC",
		    "IP" : "IP[ ]",
		    "IUP": "IUP",
		    "ISECT":"ISECT[ ]",
		    "FLIPRGON":"FLIPRGON[ ]",
		    "FLIPRGOFF":"FLIPRGOFF[ ]",
		    "MD" : "MD",
		    "MDAP":"MDAP",
		    "MDRP":"MDRP",
		    "MIAP":"MIAP",
		    "MIRP":"MIRP",
		    "MSIRP":"MSIRP",
		    "ROFF" :"ROFF[ ]",
		    "SCFS" : "SCFS[ ]",
		    "SDB" : "SDB[ ]",
		    "SDPVTL":"SDPVTL",
		    "SDS":"SDS[ ]",
		    "SFVFS":"SFVFS[ ]",
		    "SFVTL":"SFVTL",
		    "SFVTPV":"SFVTPV[ ]",
		    "SPVFS" :"SPVFS[ ]",
		    "SPVTL" :"SPVTL",
		    "SHC"  :"SHC",
		    "SHP"  :"SHP",
		    "SHPIX":"SHPIX[ ]",
		    "SHZ" : "SHZ",
		    "SLOOP":"SLOOP[ ]",
		    "SMD"  :"SMD[ ]",
		    "GETINFO":"GETINFO[ ]"
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
	    elif self.instruction == "SFVTCA":
		string = "SFVTCA["+str(self.data[0].value)+"]"
	    elif self.instruction == "SPVTCA":
		string = "SPVTCA["+str(self.data[0].value)+"]"
	    elif self.instruction == "SRP":
		if self.data[0].value == "rp0":
		    string = "SRP0[ ]"
		elif self.data[0].value	== "rp1":
		    string = "SRP1[ ]"
		else:
		    string ="SRP2[ ]"
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
    def is_roll_operation(self,current,next1,next2,next3):
        if not (isinstance(next1,AST.assignment_expression) and isinstance(next2,AST.assignment_expression) and isinstance(next3,AST.assignment_expression)):
            return False
	if not (isinstance(next1.left_oprand,AST.terminal_expression) and isinstance(next2.left_oprand,AST.terminal_expression) and isinstance(next3.left_oprand,AST.terminal_expression)):
            return False
        if not (isinstance(next1.right_oprand,AST.terminal_expression) and isinstance(next2.right_oprand,AST.terminal_expression) and isinstance(next3.right_oprand,AST.terminal_expression)):
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
	if l0 == r3 and l1 == r0 and l2 == r1 and l3 ==r2:
	    return True
        return False

    # check if this operation is a SWAP by checking current and next 2 expressions and matching pattern
    def is_swap_operation(self,current,next1,next2):
        if not (isinstance(next1,AST.assignment_expression) and isinstance(next2,AST.assignment_expression)):
            return False   
 
        if not (isinstance(next1.left_oprand,AST.terminal_expression) and isinstance(next2.left_oprand,AST.terminal_expression)):
            return False

        if not (isinstance(next1.right_oprand,AST.terminal_expression) and isinstance(next2.right_oprand,AST.terminal_expression)):
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



    def is_CINDEX_operation(self,exp):
	if len(self.variable_stack) < 1:
	    return False
	if not isinstance(self.variable_stack[-1].value,AST.terminal_expression):
            return False
	if not self.variable_stack[-1].value.type == "int":
	    return False
	index = self.variable_stack[-1].value.value
	
	if len(self.variable_stack)<index+1:
	    return False

	if not exp.left_oprand.value == self.variable_stack[-1].key.value:
	    return False

	if not isinstance(exp.right_oprand,AST.terminal_expression):
	    return False

        if not exp.right_oprand.type == "identifier":
	    return False

	if not exp.right_oprand.value == self.variable_stack[-index-1].key.value:
	    return False

	return True

    def is_MINDEX_operation(self,exp,expressions,current_itr):
	# this is done by testing step by step, it is not a MINDEX if anyone step of test fails
	# 1. check if the first exp is 'identifier' := 'identifier'
        if not isinstance(exp.right_oprand,AST.terminal_expression):
            return 0
	if not exp.right_oprand.type == 'identifier':
            return 0

	# 2. check if the first exp is 'variable_stack[-1].key := variable_stack[-2].key'
	if len(self.variable_stack) < 2:
	    return 0
	if (not self.variable(exp.left_oprand,None) == self.variable_stack[-1]) or (not self.variable(exp.right_oprand,None) == self.variable_stack[-2]):
	    return 0

	# 4. check if the second exp is 'identifier' := 'identifier'
	itr = current_itr + 1
	if len(expressions) < itr + 1:
	    return 0
        next_exp = expressions[itr]
	if not isinstance(next_exp,AST.assignment_expression):
	    return 0 
	if (not isinstance(next_exp.left_oprand,AST.terminal_expression)) or (not isinstance(next_exp.right_oprand,AST.terminal_expression)):
	    return 0
	if (not next_exp.left_oprand.type == 'identifier') or (not next_exp.right_oprand.type == 'identifier'):
	    return 0

        # 5. check if the second exp is 'variable_stack[-2].key := variable_stack[-ind].key', get ind if it is
	if not self.variable(next_exp.left_oprand,None) == self.variable_stack[-2]:
	    return 0
	if not self.variable(next_exp.right_oprand,None) in self.variable_stack:
	    return 0
	ind = self.variable_stack.index(self.variable(next_exp.right_oprand,None))
	ind = len(self.variable_stack) - ind	


	if len(expressions) < itr + ind -1 or len(self.variable_stack) < ind:
 	    return 0
	# 6. for each i from ind-2 -> 1
	# check if the next exp is 'variable_stack[len(variable_stack)-i+1].key := variable_stack[len(variable_stack)-i+2].key'
	for i in range(ind-2,1,-1):
	    itr += 1
	    next_exp = expressions[itr]
	    if not isinstance(next_exp,AST.assignment_expression):
	        return 0
	    if (not isinstance(next_exp.left_oprand,AST.terminal_expression)) or (not isinstance(next_exp.right_oprand,AST.terminal_expression)):
	        return 0
	    if (not next_exp.left_oprand.type == 'identifier') or (not next_exp.right_oprand.type == 'identifier'):
	        return 0

	    if (not self.variable(next_exp.left_oprand,None) in self.variable_stack) or (not self.variable(next_exp.right_oprand,None) in self.variable_stack):
		return 0

	    ind1 = self.variable_stack.index(self.variable(next_exp.left_oprand,None))
	    ind2 = self.variable_stack.index(self.variable(next_exp.right_oprand,None))
	    if (not ind1 == len(self.variable_stack)-i-1) or (not ind2 == len(self.variable_stack)-i):
 	        return 0
	# 7. check if the last one is 'variable_stack[-ind].key := variable_stack[-1].key'
 	itr += 1
	next_exp = expressions[itr]
	if not isinstance(next_exp,AST.assignment_expression):
	    return 0
	if (not isinstance(next_exp.left_oprand,AST.terminal_expression)) or (not isinstance(next_exp.right_oprand,AST.terminal_expression)):
	    return 0
	if (not next_exp.left_oprand.type == 'identifier') or (not next_exp.right_oprand.type == 'identifier'):
	    return 0
	if (not self.variable(next_exp.left_oprand,None) == self.variable_stack[-ind]) or (not self.variable(next_exp.right_oprand,None) == self.variable_stack[-1]):
	    return 0

 	# 8. return the index of MINDEX if all tests pass, return 0 otherwise wheneven the test fails at some step
	return ind-1


    def generate_code(self,func_AST):
	self.function = func_AST
        self.program = []
        self.variable_stack = []
	# push the function arguments into the variable stack(also change the variable name to local)
	if not func_AST.arguments is None:
            for i in range(0,len(func_AST.arguments)):
                arg_name = "arg$"+str(len(func_AST.arguments)-i)
                splits = func_AST.arguments[-i-1].split('_')
                var_name = "$fpgm_"+str(func_AST.function_num)+"_"+splits[-1]
                next_arg_var = self.variable(AST.terminal_expression("identifier",var_name),AST.terminal_expression("identifier",arg_name))
                next_arg_var.alias = arg_name
		self.variable_stack.append(next_arg_var)

	
	    
	expressions = func_AST.expressions
        self.process_expressions(expressions)

        # output bytecode,(to screen currently)
	c = []
	if func_AST.function_type == "fpgm":
	    c.append("PUSHB[ ]")
	    c.append(str(func_AST.function_num))
	    c.append("FDEF[ ]")
	for s in self.program:
	    c.append(str(s))
	if func_AST.function_type == "fpgm":
            stack_effect_with_out_POP = len(self.variable_stack) - len(func_AST.arguments)
            if stack_effect_with_out_POP > func_AST.stack_effect:
                # need extra POP[ ]s at the end
                for k in range(0,stack_effect_with_out_POP - func_AST.stack_effect):
                    c.append("POP[ ]")
	    c.append("ENDF[ ]")
	
	if func_AST.function_type == 'fpgm':
            self.code.set_code(c,func_AST.function_type,func_AST.function_num)
	elif func_AST.function_type == 'prep':
	    self.code.set_code(c,func_AST.function_type,None)
	elif func_AST.function_type == 'glyf':
	    self.code.set_code(c,func_AST.function_type,func_AST.function_tag)


	del self.program
	del self.variable_stack
	self.program = []
	self.variable_stack = []


    def process_expressions(self,expressions):
        i = 0
        while i < len(expressions):
	    exp = expressions[i]
	    # if this is an assignment exp
            if isinstance(exp,AST.assignment_expression):
		# if the left oprand of this assignment exp is terminal type(identifier)
	        if isinstance(exp.left_oprand,AST.terminal_expression):
		    if exp.left_oprand.type == "GS":
			if exp.left_oprand.value.startswith("instruction_control"):
			    s = self.statement()
			    s.instruction = "INSTCTRL"
			    self.program.append(s)
			    self.variable_stack.pop()
			    self.variable_stack.pop()
			    i += 1
			    continue
			if exp.left_oprand.value == "scan_control":
			    # this is an SCANCTRL operation
			    s = self.statement()
			    s.instruction = "SCANCTRL"
			    self.program.append(s)
			    self.variable_stack.pop()
			    i += 1
			    continue
			if exp.left_oprand.value == "scan_type":
			    s  = self.statement()
			    s.instruction = "SCANTYPE"
			    self.program.append(s)
			    self.variable_stack.pop()
			    i += 1
			    continue
			if exp.left_oprand.value.startswith("rp"):
			    for k in range(0,exp.pops):
			 	pop_stmt = self.statement()
				pop_stmt.instruction = "POP"
				self.program.append(pop_stmt)
				self.variable_stack.pop()
			    s = self.statement()
			    s.instruction = "SRP"
			    self.program.append(s)
			    self.variable_stack.pop()
			    s.data.append(exp.left_oprand)
			    i += 1
			    continue
		        if exp.left_oprand.value.startswith("zp"):
			    s = self.statement()
			    s.instruction = "SZP"
			    self.program.append(s)
			    self.variable_stack.pop()
			    s.data.append(exp.left_oprand)
			    if exp.left_oprand.is_all:
				i += 3
			    else:
			        i += 1
			    continue
			if exp.left_oprand.value == "single_width_cutin":
			    s = self.statement()
			    s.instruction = "SCVTCI"
			    self.program.append(s)
			    self.variable_stack.pop()
			    i += 1
			    continue
			if exp.left_oprand.value == "single_width_value":
			    s = self.statement()
			    s.instruction = "SSW"
			    self.program.append(s)
			    self.variable_stack.pop()
			    i += 1
			    continue
			if exp.left_oprand.value == "auto_flip":
			    s = self.statement()
			    s.instruction = "AUTOFLIP"
			    s.data.append(exp.right_oprand)
			    self.program.append(s)
			    i+=1
			    continue
		        if i+1 < len(expressions):
			 if isinstance(expressions[i+1],AST.assignment_expression): 
		          if isinstance(expressions[i+1].left_oprand,AST.terminal_expression):
			    if exp.left_oprand.value == "freedom_vector" and expressions[i+1].left_oprand.value == "projection_vector":
				    s = self.statement()
				    s.instruction = "SVTCA"
				    if exp.right_oprand.value == 0:
				        s.data.append(0)
				    else:
					s.data.append(1)
				    self.program.append(s)
				    i += 2
				    continue
			    '''
			    if exp.left_oprand.value == "auto_flip":
				s = self.statement()
			  	s.instruction = "AUTOFLIP"
				s.data.append(exp.right_oprand)
				self.program.append(s)
				i += 1
		 		continue	
			    '''
			# if this fails the test above
		        if exp.left_oprand.value == "freedom_vector":
			    if isinstance(exp.right_oprand,AST.terminal_expression):
			        if exp.right_oprand.type == "int":
				    # this is an SFVTCA[a] operation
				    s = self.statement()
				    s.instruction = "SFVTCA"
				    s.data.append(exp.right_oprand)
				    self.program.append(s)
				    i += 1
				    continue 		

		        if exp.left_oprand.value == "projection_vector":
			    if isinstance(exp.right_oprand,AST.terminal_expression):
				if exp.right_oprand.type == "int":
				    # this is an SPVTCA[a] operation
                                    s = self.statement()
                                    s.instruction = "SPVTCA"
                                    s.data.append(exp.right_oprand)
                                    self.program.append(s)
                                    i += 1
                                    continue


 
		    # if this variable is not in variable stack
                    if not self.variable(k=exp.left_oprand) in self.variable_stack:
      		        if isinstance(exp.right_oprand,AST.terminal_expression):
                            if exp.right_oprand.type == "int":
                                # this is a simple constant assignment
                                v = self.variable()
                                v.key = exp.left_oprand
                                v.value = exp.right_oprand
                                self.variable_stack.append(v)
                                s = self.statement()
                                s.instruction = "PUSH"
                                s.data.append(exp.right_oprand)
                                self.program.append(s)
                                i += 1
			        continue
			    elif exp.right_oprand.type == "MPPEM":
			        # this is an MPPEM operation
				v = self.variable()
				v.key = exp.left_oprand
				v.value = exp.right_oprand
				self.variable_stack.append(v)
				s = self.statement()
				s.instruction = "MPPEM"
				s.data.append(exp.right_oprand)
				self.program.append(s)
				i += 1
				continue
			    elif exp.right_oprand.type == "PointSize":
				# this is an MPS operation
				v = self.variable()
                                v.key = exp.left_oprand
                                v.value = exp.right_oprand
                                self.variable_stack.append(v)
                                s = self.statement()
                                s.instruction = "MPS"
                                s.data.append(exp.right_oprand)
                                self.program.append(s)
                                i += 1
                                continue
 


                            elif exp.right_oprand.type == "identifier":
                                # if the right side is an identifier, it could be copy/swap/roll instruction...

                                # 1. check if this is a roll,by checking the next 3 expressions
                                if len(expressions) > i+3 and len(self.variable_stack)>2:
                                    next1 = expressions[i+1]
                                    next2 = expressions[i+2]
                                    next3 = expressions[i+3]
				    if self.is_roll_operation(exp,next1,next2,next3):
                                        # this is a roll operation,roll the top 3 variables,roll the values of top 3 variables
                                        temp = self.variable_stack[-1].value
                                        exp.left_oprand.value
                                        self.variable_stack[-1].value = self.variable_stack[-3].value
                                        self.variable_stack[-3].value = self.variable_stack[-2].value
                                        self.variable_stack[-2].value = temp
                                        s = self.statement()
                                        s.instruction = "ROLL"
                                        self.program.append(s)
                                        i = i + 3 + 1
                                        continue




                                # 2. check if this is a swap,by checking the next 2 expressions
                                if len(expressions) > i+2 and len(self.variable_stack)>1:
                                    next1 = expressions[i+1]
                                    next2 = expressions[i+2]
			            if self.is_swap_operation(exp,next1,next2):
				        # this is a swap operation,swap the values of top 2 variables
                                        temp = self.variable_stack[-1].value
                                        self.variable_stack[-1].value = self.variable_stack[-2].value
                                        self.variable_stack[-2].value = temp
                                        s = self.statement()
                                        s.instruction = "SWAP"
                                        self.program.append(s)
                                        i = i + 3
		                        continue

                                # 3. check if this is a copy,(it fails 1,but pass 2,->it's a copy)
				if len(self.variable_stack) > 0:
                                    if exp.right_oprand.value == self.variable_stack[-1].key.value:
                                        s = self.statement()
                                        s.instruction = "COPY"
                                        self.program.append(s)
                                        v = self.variable()
                                        v.key = exp.left_oprand
                                        v.value = self.variable_stack[-1].value
                                        self.variable_stack.append(v)
                                        i += 1
                                        continue
			    elif exp.right_oprand.type == "GS":
				if exp.right_oprand.value == "freedom_vector_0":
				    if isinstance(expressions[i+1],AST.assignment_expression):
				        if isinstance(expressions[i+1].right_oprand,AST.terminal_expression):
					    if expressions[i+1].right_oprand.type == "GS" and expressions[i+1].right_oprand.value == "freedom_vector_1":
					        # this is a GFV operation
			                        s = self.statement()
				                s.instruction = "GFV"
				                s.data.append(exp)
				                self.program.append(s)
				                self.variable_stack.append(self.variable(exp.left_oprand,"free_vector_0"))
				                self.variable_stack.append(self.variable(expressions[i+1].left_oprand,"free_vector_1"))
				                i += 2
				                continue	
                                elif exp.right_oprand.value == "projection_vector_0":
                                    if isinstance(expressions[i+1],AST.assignment_expression):
                                        if isinstance(expressions[i+1].right_oprand,AST.terminal_expression):
                                            if expressions[i+1].right_oprand.type == "GS" and expressions[i+1].right_oprand.value == "projection_vector_1":
                                                # this is a GPV operation
                                                s = self.statement()
                                                s.instruction = "GPV"
                                                s.data.append(exp)
                                                self.program.append(s)
                                                self.variable_stack.append(self.variable(exp.left_oprand,"projection_vector_0"))
                                                self.variable_stack.append(self.variable(expressions[i+1].left_oprand,"projection_vector_1"))
                                                i += 2
						ne = expressions[i]
                                                continue                


			


		


                        else:
			    if isinstance(exp.right_oprand,AST.roundState_expression):
                                s = self.statement()
                                s.instruction = exp.right_oprand.type
                                self.program.append(s)
				if exp.right_oprand.type in ["RoundState_Super","RoundState_45"]:
				    self.variable_stack.pop()
                                i += 1
                                continue
			    elif isinstance(exp.right_oprand,AST.methodCall_expression):
			        if exp.right_oprand.methodName == "GC":
				    s = self.statement()
				    s.instruction = "methodCall"
				    s.data.append(exp.right_oprand)
				    self.program.append(s)
				    self.variable_stack[-1].value = dataType.AbstractValue()

				        
                                        

                    # this is assignment exp->left oprand is terminal(identifier)->identifier is in variable stack                
                    else:
			if self.is_MINDEX_operation(exp,expressions,i)>0:
			    # this is a MINDEX operation
			    skip = self.is_MINDEX_operation(exp,expressions,i)
			    self.variable_stack[-1].value = self.variable_stack[-skip-1].value
			    for k in range(skip,0,-1):
				self.variable_stack[-k-1].value = self.variable_stack[-k].value
			    self.variable_stack.pop()

			    s = self.statement()
			    s.instruction = "MINDEX"
			    self.program.append(s)
			    i += skip+1
			    continue
			    


		        if self.is_CINDEX_operation(exp):
		            # this is a CINDEX operation
			    index = self.variable_stack[-1].value.value
                            self.variable_stack[-1].value = self.variable_stack[-index-1].value		   
			    s = self.statement()
			    s.instruction = "CINDEX"
			    self.program.append(s)
			    i += 1
			    continue
		        elif isinstance(exp.right_oprand,AST.IndexedStorage_expression):
			    if len(self.variable_stack)>0:
			        if self.variable_stack[-1].key.value == exp.left_oprand.value:
			            # this is a Read indexed storage operation
				    s = self.statement()
				    s.instruction = "readIndexedStorage"
				    s.data.append(exp.right_oprand)
				    self.program.append(s)
				    self.variable_stack[-1].value = exp.right_oprand
				    i += 1
			            continue
			elif isinstance(exp.right_oprand,AST.binary_expression):
			    self.variable_stack.pop()
			    self.variable_stack[-1].value = exp.right_oprand
			    s = self.statement()
			    s.instruction = "binary"
			    s.data.append(exp.right_oprand)
			    self.program.append(s)
			    i += 1
		            continue


			elif isinstance(exp.right_oprand,AST.unary_expression):
			    if len(self.variable_stack)>0:
			        if self.variable_stack[-1].key.value == exp.left_oprand.value:
			            s = self.statement()
			            s.instruction = "unary"
			            s.data.append(exp.right_oprand.op)
			            self.program.append(s)
			            self.variable_stack[-1].value = exp.right_oprand
				    i += 1
				    continue
			elif isinstance(exp.right_oprand,AST.methodCall_expression):
			    s = self.statement()
			    s.instruction = "methodCall"
			    s.data.append(exp.right_oprand)
			    self.variable_stack[-1].value = exp.right_oprand
			    self.program.append(s)
			    i += 1
			    continue
		        else:
			    # if the variable is in the stack and nothing above is satisfied
			    # it is regarded that there are pop operations before here
			    temp_var = self.variable(exp.left_oprand,None)
			    index = len(self.variable_stack) - self.variable_stack.index(temp_var)
			    for itr in range(0,index):
				s = self.statement()
				s.instruction = "POP"
				self.program.append(s)
			        self.variable_stack.pop()
			    continue



	        # this is an assignment exp -> left oprand is not terminal_expression(identifier)
                else:
		    if isinstance(exp.left_oprand,AST.IndexedStorage_expression):
			if isinstance(exp.right_oprand,AST.terminal_expression):
			    if (self.variable_stack) > 1:
				    #this is a write to storage
				    self.variable_stack.pop()
				    self.variable_stack.pop()
				    s = self.statement()
				    s.instruction = "writeToIndexedStorage"
				    s.data.append(exp.left_oprand)
				    self.program.append(s)
				    i += 1
				    continue
	    # this is not an assignment exp
            else:
		if isinstance(exp,AST.if_expression):
		    # declare variable stack backup variables
		    var_stack_after_if_branch = None
		    var_stack_after_else_branch = None
		    var_stack_backup = None

		    # push if instruction, pop a variable from variable_stack
		    if_stmt = self.statement()
		    if_stmt.instruction = "IF"
		    self.program.append(if_stmt)
		    self.variable_stack.pop()
		
		    # deepcopy current variable stack to var_stack_backup
		    var_stack_backup = copy.deepcopy(self.variable_stack)
		    
	 	    # process if branch
		    self.process_expressions(exp.if_branch)

		    # deepcopy current variable stack to var_stack_after_if_branch
		    var_stack_after_if_branch = copy.deepcopy(self.variable_stack)
		
		    # if else branch is not empty
		    if len(exp.else_branch) > 0:
			# push else statement 
			else_stmt = self.statement()
			else_stmt.instruction = "ELSE"
			self.program.append(else_stmt)
			# get the position(index) of else statement
			else_stmt_index = len(self.program)-1
			# restore the variable stack and process the else branch
			self.variable_stack = copy.deepcopy(var_stack_backup)
		        self.process_expressions(exp.else_branch)
			# deepcopy current variable stack to var_stack_after_else_branch
			var_stack_after_else_branch = copy.deepcopy(self.variable_stack)
			
			## configure pop instructions at the end of if/else branches
			#  if else branch has more variables, need pops at the end of else branch
			if len(var_stack_after_else_branch) > len(var_stack_after_if_branch):
			    num_to_pop = len(var_stack_after_else_branch) - len(var_stack_after_if_branch)
			    for k in range(0,num_to_pop):
				# append pop statment at the end of program and pop a variable from else_branch
				pop_stmt = self.statement()
				pop_stmt.instruction = "POP"
				self.program.append(pop_stmt)
				var_stack_after_else_branch.pop()
			
				

			#  if if branch has more variables, need pops at the end of if branch
			elif len(var_stack_after_if_branch) > len(var_stack_after_else_branch):
			    num_to_pop = len(var_stack_after_if_branch) - len(var_stack_after_else_branch)
			    pos = else_stmt_index
			    for k in range(0,num_to_pop):
			        # insert pop statement to the index of else statement
				pop_stmt = self.statement()
				pop_stmt.instruction = "POP"
				self.program.insert(pos,pop_stmt)
				pos += 1
			  	# pop a variable from if branch
				var_stack_after_if_branch.pop()

			# append eif statement
			eif_stmt = self.statement()
			eif_stmt.instruction = "EIF"
			self.program.append(eif_stmt)
			# set current variable stack to var_stack_after_else_branch (or var_stack_after_if_branch)		
			self.variable_stack = var_stack_after_else_branch

		    # if else branch is empty, var stack after "else branch" is backup var stack
		    else:
			# if the if branch reduced the variable stack size, need else branch with pops
			if len(var_stack_backup) > len(var_stack_after_if_branch):
			    num_to_pop = len(var_stack_backup) - len(var_stack_after_if_branch)
			    # append else statement
			    else_stmt = self.statement()
			    else_stmt.instruction = "ELSE"
			    self.program.append(else_stmt)
			    for k in range(0,num_to_pop):
				# append pop statement, and pop a variable from var_stack_backup
				pop_stmt = self.statement()
				pop_stmt.instruction = "POP"
				self.program.append(pop_stmt)
				var_stack_backup.pop()

			# if the if branch increased the variable stakc size, need pops at the end of the if branch
			elif len(var_stack_after_if_branch) > len(var_stack_backup):
			    num_to_pop = len(var_stack_after_if_branch) - len(var_stack_backup)
			    for k in range(0,num_to_pop):
				# append pop to the end and pop a variable from var_stack_after_if_branch
				pop_stmt = self.statement()
				pop_stmt.instruction = "POP"	
				self.program.append(pop_stmt)
				var_stack_after_if_branch.pop()
		
		        # append eif statement
                        eif_stmt = self.statement()
                        eif_stmt.instruction = "EIF"
                        self.program.append(eif_stmt)
		        # set the current variable stack to var_stack_backup (or var_stack_after_if_branch)
		        self.variable_stack = var_stack_backup

		    # increment program pointer and continue
		    i += 1
		    continue


	        elif isinstance(exp,AST.methodCall_expression):
		    s = self.statement()
		    s.instruction = "methodCall"
		    s.data.append(exp)
		    self.program.append(s)
		    if exp.methodName == "MSIRP":
		        self.variable_stack.pop()
		        self.variable_stack.pop() 

		    elif exp.methodName == "ALIGNRP":
			for k in range(0,exp.data):
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
			    for k in range(0,-exp.stack_effect*repeats):
			        self.variable_stack.pop()
			elif exp.stack_effect > 0:
			    tag = self.variable_stack[-1].key.value.split('_')[0]
			    if self.function.function_type == "fpgm":
				tag = tag + '_' + str(self.function.function_num) + '_'
			    else:
				tag = tag + '_'


			    for k in range(0,exp.stack_effect*repeats):
				var_key_str = tag + str(len(self.variable_stack)+1)
				var_val_str = '$arg_' + str(k+1)
				var = self.variable(AST.terminal_expression("identifier",var_key_str),AST.terminal_expression("identifier",var_val_str))
				self.variable_stack.append(var)


		    elif exp.methodName == "AA":
		        self.variable_stack.pop()
		    elif exp.methodName == "ALIGNPTS":
			self.variable_stack.pop()
			self.variable_stack.pop()
		    elif exp.methodName == "DELTA":
			self.variable_stack.pop()
			for k in range(0,len(exp.args)):
			    self.variable_stack.pop()
		    elif exp.methodName == "IP":
			for k in range(0,len(exp.args)):
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
			for k in range(0,len(exp.args)):
			    self.variable_stack.pop()
		    elif exp.methodName == "SHPIX":
			for k in range(0,exp.pops):
			    pop_stmt = self.statement()
			    pop_stmt.instruction = "POP"
			    self.program.insert(len(self.program)-1,pop_stmt)
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
			for k in range(0,5):
			   self.variable_stack.pop()

		    i += 1
		    continue
		
            i += 1
                    #index = self.variable_stack.index(self.variable(k=exp.left_oprand))
                    #offset = len(self.variable_stack) - index






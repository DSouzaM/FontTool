from fontTools.ttLib.data import dataType
import math
import copy
import sys
sys.path.append('/home/zeming/Desktop/projects/fonttools/Lib/compiler')
import AST

class Boolean(object):
    def __init__(self, value):
        self.value = value
    def __repr__(self):
        return self.value

class Constant(object):
    def __init__(self, value):
        self.value = value
    def eval(self, keep_abstract):
        return self.value
    def __repr__(self):
        return str(self.value)

class Variable(dataType.AbstractValue):
    def __init__(self, identifier, data = None):
        self.identifier = identifier
        self.data = data
    def eval(self, keep_abstract):
        if keep_abstract or self.data is None:
            return self
        if isinstance(self.data, dataType.AbstractValue):
            return self.data.eval(keep_abstract)
        else:
            return self.data
    def __repr__(self):
        return self.identifier
    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.__dict__ == other.__dict__
        else:
            return False

class GraphicsStateVariable(Variable):
    def __repr__(self):
        return self.identifier

class AutoFlip(GraphicsStateVariable):
    def __init__(self):
        self.data = None
        self.identifier = 'GS[auto_flip]'
    
class DeltaBase(GraphicsStateVariable):
    def __init__(self):
        self.data = None
        self.identifier = 'GS[delta_base]'

class DeltaShift(GraphicsStateVariable):
    def __init__(self):
        self.data = None
        self.identifier = 'GS[delta_shift]'

class FreedomVector(GraphicsStateVariable):
    def __init__(self):
        self.data = None
        self.identifier = 'GS[freedom_vector]'

class FreedomVectorByComponent(GraphicsStateVariable):
    def __init__(self, selector):
        self.data = None
        self.selector = selector
        self.identifier = 'GS[freedom_vector_%s]' % self.selector

class DualProjectionVector(GraphicsStateVariable):
    def __init__(self):
        self.data = None
        self.identifier = 'GS[dual_projection_vector]'

class InstructControl(GraphicsStateVariable):
    def __init__(self, selector):
        self.selector = selector
        self.data = None
        self.identifier = 'GS[instruction_control_%s]' % self.selector

class LoopValue(GraphicsStateVariable):
    def __init__(self):
        self.data = None
        self.identifier = 'GS[loop]'

class MinimumDistance(GraphicsStateVariable):
    def __init__(self):
        self.data = None
        self.identifier = 'GS[minimum_distance]'

class ControlValueCutIn(GraphicsStateVariable):
    def __init__(self):
        self.data = None
        self.identifier = 'GS[control_value_cutin]'

class RoundState(GraphicsStateVariable):
    def __init__(self):
        self.data = None
        self.identifier = 'GS[round_state]'

class RP0(GraphicsStateVariable):
    def __init__(self):
        self.data = None
        self.identifier = 'GS[rp0]'

class RP1(GraphicsStateVariable):
    def __init__(self):
        self.data = None
        self.identifier = 'GS[rp1]'

class RP2(GraphicsStateVariable):
    def __init__(self):
        self.data = None
        self.identifier = 'GS[rp2]'

class ScanControl(GraphicsStateVariable):
    def __init__(self):
        self.data = None
        self.identifier = 'GS[scan_control]'

class ScanType(GraphicsStateVariable):
    def __init__(self):
        self.data = None
        self.identifier = 'GS[scan_type]'

class SingleWidthCutIn(GraphicsStateVariable):
    def __init__(self):
        self.data = None
        self.identifier = 'GS[single_width_cutin]'

class SingleWidthValue(GraphicsStateVariable):
    def __init__(self):
        self.data = None
        self.identifier = 'GS[single_width_value]'

class ZP0(GraphicsStateVariable):
    def __init__(self):
        self.data = None
        self.identifier = 'GS[zp0]'

class ZP1(GraphicsStateVariable):
    def __init__(self):
        self.data = None
        self.identifier = 'GS[zp1]'

class ZP2(GraphicsStateVariable):
    def __init__(self):
        self.data = None
        self.identifier = 'GS[zp2]'

class ProjectionVector(GraphicsStateVariable):
    def __init__(self):
        self.data = None
        self.identifier = 'GS[projection_vector]'

class ProjectionVectorByComponent(GraphicsStateVariable):
    def __init__(self, selector):
        self.data = None
        self.selector = selector
        self.identifier = 'GS[projection_vector_%s]' % self.selector

class GlobalDictionary(Variable):
    def __init__(self):
        self.storage = {}
    def read(self,index):
        return self.storage[index]
    def write(self, index, val):
        self.storage[index] = val
class CVTTable(GlobalDictionary):
    pass
class StorageArea(GlobalDictionary):
    pass

class InputVariable(Variable):
    pass

class Operator(object):
    pass

class AssignOperator(Operator):
    def __repr__(self):
        return ":="
class ADDOperator(Operator):
    def __repr__(self):
        return "+"
class SUBOperator(Operator):
    def __repr__(self):
        return "-"
class MULOperator(Operator):
    def __repr__(self):
        return "*"
class DIVOperator(Operator):
    def __repr__(self):
        return "/"
class MAXOperator(Operator):
    def __repr__(self):
        return "max"
class MINOperator(Operator):
    def __repr__(self):
        return "min"

class ANDOperator(Operator):
    def __repr__(self):
        return "AND"
class OROperator(Operator):
    def __repr__(self):
        return "OR"
class GTOperator(Operator):
    def __repr__(self):
        return "GT"
class GTEQOperator(Operator):
    def __repr__(self):
        return "GE"
class LTOperator(Operator):
    def __repr__(self):
        return "LT"
class LTEQOperator(Operator):
    def __repr__(self):
        return "LE"
class EQOperator(Operator):
    def __repr__(self):
        return "EQ"
class NEQOperator(Operator):
    def __repr__(self):
        return "NE"

class NEGOperator(Operator):
    def __repr__(self):
        return "NEG"

class Expression(dataType.AbstractValue):
    pass

class UnaryExpression(Expression):
    def __init__(self, arg, op):
	self.arg = arg
	self.operator = op
    def eval(self, keep_abstract):
        if (keep_abstract):
            return self
        ue = copy.copy(self)
        ue.arg = ue.arg.eval(keep_abstract)
        return ue
    def __repr__(self):
	return "%s %s" % (str(self.operator), self.arg)

class BinaryExpression(Expression):
    def __init__(self, left, right, op):
	self.left = left
	self.right = right
	self.operator = op
    def eval(self, keep_abstract):
        if (keep_abstract):
            return self
        be = copy.copy(self)
        be.left = be.left.eval(keep_abstract)
        be.right = be.right.eval(keep_abstract)
        return be

class InfixBinaryExpression(BinaryExpression):
    def __init__(self, left, right, op):
        super(InfixBinaryExpression, self).__init__(left, right, op)
    def __repr__(self):
	return "%s %s %s" % (self.left, str(self.operator), self.right)

class PrefixBinaryExpression(BinaryExpression):
    def __init__(self, left, right, op):
        super(PrefixBinaryExpression, self).__init__(left, right, op)
    def __repr__(self):
	return "%s(%s, %s)" % (str(self.operator), self.left, self.right)

class MethodCallStatement(object):
    def __init__(self, parameters = [], returnVal=None):
    	self.parameters = parameters
        self.returnVal = returnVal
    def setParameters(self, parameters):
        self.parameters = parameters
    def setReturnVal(self, returnVal):
        self.returnVal = returnVal
    def __repr__(self):
	if isinstance(self,CallStatement):
            return '%sCALL%s %s%s' % (self.call_rv, self.repeats, str(self.callee), self.call_args)
        repS = ''
        if self.returnVal is not None:
            repS = str(self.returnVal) + ' := '
    	repS += '{}('.format(self.methodName)
        repS += ','.join(map(lambda x: str(x.identifier), self.parameters))
        repS += ')'
	return repS

    def push_expression(self,func_tree):
        # func call statement comes first
        if isinstance(self,CallStatement):
	    exp = AST.call_expression(self.callee,self.stack_effect,self.call_arg_list)
	    if isinstance(self.callee,list):
		exp = AST.call_expression(self.callee[0],self.stack_effect,self.call_arg_list)
	    if len(self.repeats) > 0:
		cn = int(self.repeats[1:len(self.repeats)])
		exp.cn = cn

	    func_tree.push_expression(exp)
	    return

	if self.returnVal is not None:
            exp = AST.assignment_expression()
	    if isinstance(self.returnVal,Variable):
	        exp.left_oprand = AST.terminal_expression("identifier",self.returnVal.identifier)
	    else:
		exp.left_oprand = AST.terminal_expression("identifier",self.returnVal)

	    exp.right_oprand = AST.methodCall_expression()
	    if isinstance(self,GCMethodCall):
		exp.right_oprand.methodName = "GC"
		exp.right_oprand.data = self.data
		exp.right_oprand.parameters = self.parameters
	    else:
	        exp.right_oprand.methodName = self.methodName
	        exp.right_oprand.parameters = self.parameters
	    func_tree.push_expression(exp)
	else:
	    if isinstance(self,MSIRPMethodCall):
		exp = AST.methodCall_expression("MSIRP",self.data.value,self.parameters)
	    elif isinstance(self,AAMethodCall):
	        exp = AST.methodCall_expression("AA",None,self.parameters)
	    elif isinstance(self,ALIGNRPMethodCall):
		exp = AST.methodCall_expression("ALIGNRP",self.loop_value,None)
	    elif isinstance(self,DELTAMethodCall):
		exp = AST.methodCall_expression("DELTA",self.op,self.parameters)
	    elif isinstance(self,IPMethodCall):
		exp = AST.methodCall_expression("IP",None,self.parameters)
	    elif isinstance(self,IUPMethodCall):
		exp = AST.methodCall_expression("IUP",self.data.value,None)
	    elif isinstance(self,MDMethodCall):
		exp = AST.methodCall_expression("MD",self.data.value,self.parameters)
	    elif isinstance(self,MDAPMethodCall):
		exp = AST.methodCall_expression("MDAP",self.data.value,self.parameters)
	    elif isinstance(self,MDRPMethodCall):
		exp = AST.methodCall_expression("MDRP",self.data.value,self.parameters)
	    elif isinstance(self,MIAPMethodCall):
		exp = AST.methodCall_expression("MIAP",self.data.value,self.parameters)
	    elif isinstance(self,MIRPMethodCall):
		exp = AST.methodCall_expression("MIRP",self.data.value,self.parameters)
	    elif isinstance(self,MSIRPMethodCall):
		exp = AST.methodCall_expression("MSIRP",self.data.value,self.parameters)
	    elif isinstance(self,ROFFMethodCall):
		exp = AST.methodCall_expression("ROFF",None,None)
	    elif isinstance(self,ISECTMethodCall):
	        exp = AST.methodCall_expression("ISECT",None,self.parameters)
	    elif isinstance(self,SCFSMethodCall):
		exp = AST.methodCall_expression("SCFS",None,self.parameters)
	    elif isinstance(self,SPVTLMethodCall):
		exp = AST.methodCall_expression("SPVTL",self.data.value,self.parameters)
	    elif isinstance(self,SFVTPVMethodCall):
	        exp = AST.methodCall_expression("SFVTPV",None,self.parameters)
	    elif isinstance(self,SPVFSMethodCall):
  	        exp = AST.methodCall_expression("SPVFS",None,self.parameters)
	    elif isinstance(self,SDBMethodCall):
		exp = AST.methodCall_expression("SDB",None,self.parameters)
	    elif isinstance(self,SDPVTLMethodCall):
		exp = AST.methodCall_expression("SDPVTL",self.data.value,self.parameters)
	    elif isinstance(self,SDSMethodCall):
		exp = AST.methodCall_expression("SDS",None,self.parameters)
	    elif isinstance(self,SFVFSMethodCall):
		exp = AST.methodCall_expression("SFVFS",None,self.parameters)
	    elif isinstance(self,SFVTLMethodCall):
		exp = AST.methodCall_expression("SFVTL",self.data.value,self.parameters)
	    elif isinstance(self,SHCMethodCall):
		exp = AST.methodCall_expression("SHC",self.data.value,self.parameters)
	    elif isinstance(self,SHPMethodCall):
		exp = AST.methodCall_expression("SHP",self.data.value,self.parameters)
	    elif isinstance(self,SHPIXMethodCall):
		exp = AST.methodCall_expression("SHPIX",None,self.parameters)
            elif isinstance(self,SHZMethodCall):
                exp = AST.methodCall_expression("SHZ",self.data.value,self.parameters)
            elif isinstance(self,SLOOPMethodCall):
                exp = AST.methodCall_expression("SLOOP",None,self.parameters)
            elif isinstance(self,SMDMethodCall):
                exp = AST.methodCall_expression("SMD",None,self.parameters)

	    else:
                exp = AST.expression()
	    func_tree.push_expression(exp)

class AAMethodCall(MethodCallStatement):
    def __init__(self,parameters = [], returnVal = None):
        super(AAMethodCall,self).__init__(parameters,returnVal)
	self.methodName = 'AA'

class ALIGNPTSMethodCall(MethodCallStatement):
    def __init__(self,parameters = [], returnVal = None):
        super(ALIGNPTSMethodCall,self).__init__(parameters,returnVal)
        self.methodName = 'ALIGNPTS'


class SDBMethodCall(MethodCallStatement):
    def __init__(self, parameters = [], returnVal=None):
        super(SDBMethodCall, self).__init__(parameters, returnVal)
        self.methodName = 'SDB'

class DELTAMethodCall(MethodCallStatement):
    def __init__(self, op, parameters = [], returnVal=None):
        super(DELTAMethodCall, self).__init__(parameters, returnVal)
	self.op = op
        self.methodName = 'DELTA' + op

class MINMethodCall(MethodCallStatement):
    def __init__(self, parameters = [], returnVal=None):
        super(MINMethodCall, self).__init__(parameters, returnVal)
        self.methodName = 'MIN'

class MAXMethodCall(MethodCallStatement):
    def __init__(self, parameters = [], returnVal=None):
        super(MAXMethodCall, self).__init__(parameters, returnVal)
        self.methodName = 'MAX'

class ALIGNPTSMethodCall(MethodCallStatement):
    def __init__(self, parameters = [], returnVal=None):
        super(ALIGNPTSMethodCall, self).__init__(parameters, returnVal)
        self.methodName = 'ALIGNPT'

class ABSMethodCall(MethodCallStatement):
    def __init__(self, parameters = [], returnVal=None):
        super(ABSMethodCall, self).__init__(parameters, returnVal)
        self.methodName = 'ABS'
    def eval(self, keep_abstract):
        p = self.parameters[0].eval(keep_abstract)
        if isinstance(p, dataType.AbstractValue):
            return self
        return math.fabs(p)

class CEILMethodCall(MethodCallStatement):
    def __init__(self, parameters = [], returnVal=None):
        super(CEILINGMethodCall, self).__init__(parameters, returnVal)
        self.methodName = 'CEIL'
    def eval(self, keep_abstract):
        p = self.parameters[0].eval(keep_abstract)
        if isinstance(p, dataType.AbstractValue):
            return self
        return math.ceil(p)

class FLOORMethodCall(MethodCallStatement):
    def __init__(self, parameters = [], returnVal=None):
        super(FLOORMethodCall, self).__init__(parameters, returnVal)
        self.methodName = 'FLOOR'
    def eval(self, keep_abstract):
        p = self.parameters[0].eval(keep_abstract)
        if isinstance(p, dataType.AbstractValue):
            return self
        return math.floor(p)

class NOTMethodCall(MethodCallStatement):
    def __init__(self, parameters = [], returnVal=None):
        super(NOTMethodCall, self).__init__(parameters, returnVal)
        self.methodName = 'NOT'
    def eval(self, keep_abstract):
        p = self.parameters[0].eval(keep_abstract)
        if p == 0:
            return 1
        elif p == 1:
            return 0
        return self

class MIRPMethodCall(MethodCallStatement):
    def __init__(self, parameters = [], returnVal=None):
        super(MIRPMethodCall, self).__init__(parameters, returnVal)
        self.methodName = 'MIRP'

class ROFFMethodCall(MethodCallStatement):
    def __init__(self,parameters = [],returnVal=None):
        super(ROFFMethodCall,self).__init__(parameters,returnVal)
        self.methodName = 'ROFF'



class GCMethodCall(MethodCallStatement):
    def __init__(self, data, parameters = [], returnVal=None):
        super(GCMethodCall, self).__init__(parameters, returnVal)
	self.data = data
        self.methodName = 'GC_'+data

class GETINFOMethodCall(MethodCallStatement):
    def __init__(self, parameters = [], returnVal=None):
        super(GETINFOMethodCall, self).__init__(parameters, returnVal)
        self.methodName = 'GETINFO'
    def eval(self, keep_abstract):
        return self

class ALIGNRPMethodCall(MethodCallStatement):
    def __init__(self, parameters = [], returnVal=None,loop_value = 1):
        super(ALIGNRPMethodCall, self).__init__(parameters, returnVal)
        self.methodName = 'ALIGNRP'
	self.loop_value = loop_value

class IPMethodCall(MethodCallStatement):
    def __init__(self, parameters = [], returnVal=None):
        super(IPMethodCall, self).__init__(parameters, returnVal)
        self.methodName = 'IP'

class ISECTMethodCall(MethodCallStatement):
    def __init__(self,parameters = [], returnVal=None):
        super(ISECTMethodCall,self).__init__(parameters,returnVal)
	self.methodName = 'ISECT'

class ROUNDMethodCall(MethodCallStatement):
    def __init__(self, data, parameters = [], returnVal=None):
        super(ROUNDMethodCall, self).__init__(parameters, returnVal)
	self.data = data
        self.methodName = 'ROUND_'+data.value

class SPVFSMethodCall(MethodCallStatement):
    def __init__(self,parameters=[],returnVal=None):
        super(SPVFSMethodCall,self).__init__(paramters,returnVal)
        self.methodName = "SPVFS"

class SPVTLMethodCall(MethodCallStatement):
    def __init__(self,data,parameters = [],returnVal=None):
        super(SPVTLMethodCall,self).__init__(parameters,returnVal)
	self.data = data
	self.methodName = "SPVTL"

class SHPMethodCall(MethodCallStatement):
    def __init__(self, data, parameters = [], returnVal=None):
        super(SHPMethodCall, self).__init__(parameters, returnVal)
	self.data = data
        self.methodName = 'SHP_'+data.value

class SHPIXMethodCall(MethodCallStatement):
    def __init__(self, parameters = [], returnVal=None):
        super(SHPIXMethodCall, self).__init__(parameters, returnVal)
        self.methodName = 'SHPIX'

class IUPMethodCall(MethodCallStatement):
    def __init__(self, data, parameters = [], returnVal=None):
        super(IUPMethodCall, self).__init__(parameters, returnVal)
	self.data = data
        self.methodName = 'IUP_'+data.value

class MDMethodCall(MethodCallStatement):
    def __init__(self, data, parameters = [], returnVal=None):
        super(MDMethodCall, self).__init__(parameters, returnVal)
	self.data = data
        self.methodName = 'MD_'+data.value

class MDAPMethodCall(MethodCallStatement):
    def __init__(self, data, parameters = [], returnVal=None):
        super(MDAPMethodCall, self).__init__(parameters, returnVal)
	self.data = data
        self.methodName = 'MDAP_'+data.value

class MDRPMethodCall(MethodCallStatement):
    def __init__(self, data, parameters = [], returnVal=None):
	self.data = data
        super(MDRPMethodCall, self).__init__(parameters, returnVal)
        self.methodName = 'MDRP_'+data.value

class MIAPMethodCall(MethodCallStatement):
    def __init__(self, data, parameters = [], returnVal=None):
        super(MIAPMethodCall, self).__init__(parameters, returnVal)
	self.data = data
        self.methodName = 'MIAP_'+data.value

class MIRPMethodCall(MethodCallStatement):
    def __init__(self, data, parameters = [], returnVal=None):
        super(MIRPMethodCall, self).__init__(parameters, returnVal)
	self.data = data
        self.methodName = 'MIRP_'+data.value

class MSIRPMethodCall(MethodCallStatement):
    def __init__(self, data, parameters = [], returnVal=None):
        super(MSIRPMethodCall, self).__init__(parameters, returnVal)
	self.data = data
	self.args = parameters
        self.methodName = 'MSIRP_'+data.value

class SCFSMethodCall(MethodCallStatement):
    def __init__(self, parameters = [], returnVal=None):
        super(SCFSMethodCall, self).__init__(parameters, returnVal)
        self.methodName = 'SCFS'

class SDPVTLMethodCall(MethodCallStatement):
    def __init__(self, data, parameters = [], returnVal=None):
        super(SDPVTLMethodCall, self).__init__(parameters, returnVal)
	self.data = data
        self.methodName = 'SDPVTL_'+data.value

class SDSMethodCall(MethodCallStatement):
    def __init__(self, parameters = [], returnVal=None):
        super(SDSMethodCall, self).__init__(parameters, returnVal)
        self.methodName = 'SDS'

class SFVFSMethodCall(MethodCallStatement):
    def __init__(self, parameters = [], returnVal=None):
        super(SFVFSMethodCall, self).__init__(parameters, returnVal)
        self.methodName = 'SFVFS'

class SFVTLMethodCall(MethodCallStatement):
    def __init__(self, data, parameters = [], returnVal=None):
        super(SFVTLMethodCall, self).__init__(parameters, returnVal)
	self.data  = data
        self.methodName = 'SFVTL_'+data.value

class SFVTPVMethodCall(MethodCallStatement):
    def __init__(self,parameters=[],returnVal=None):
        super(SFVTPVMethodCall,self).__init__(parameters,returnVal)
	self.methodName = "SFVTPV"

class SHCMethodCall(MethodCallStatement):
    def __init__(self, data, parameters = [], returnVal=None):
        super(SHCMethodCall, self).__init__(parameters, returnVal)
	self.data = data
        self.methodName = 'SHC_'+data.value

class SHZMethodCall(MethodCallStatement):
    def __init__(self, data, parameters = [], returnVal=None):
        super(SHZMethodCall, self).__init__(parameters, returnVal)
	self.data = data
        self.methodName = 'SHZ_'+data.value

class SLOOPMethodCall(MethodCallStatement):
    def __init__(self, parameters = [], returnVal=None):
        super(SLOOPMethodCall, self).__init__(parameters, returnVal)
        self.methodName = 'SLOOP'

class SMDMethodCall(MethodCallStatement):
    def __init__(self, parameters = [], returnVal=None):
        super(SMDMethodCall, self).__init__(parameters, returnVal)
        self.methodName = 'SMD'

class SRP0MethodCall(MethodCallStatement):
    def __init__(self, parameters = [], returnVal=None):
        super(SRP0MethodCall, self).__init__(parameters, returnVal)
        self.methodName = 'SRP0'

class SRP1MethodCall(MethodCallStatement):
    def __init__(self, parameters = [], returnVal=None):
        super(SRP1MethodCall, self).__init__(parameters, returnVal)
        self.methodName = 'SRP1'

class SRP2MethodCall(MethodCallStatement):
    def __init__(self, parameters = [], returnVal=None):
        super(SRP2MethodCall, self).__init__(parameters, returnVal)
        self.methodName = 'SRP2'

class SZP0MethodCall(MethodCallStatement):
    def __init__(self, parameters = [], returnVal=None):
        super(SZP0MethodCall, self).__init__(parameters, returnVal)
        self.methodName = 'SZP0'

class SZP1MethodCall(MethodCallStatement):
    def __init__(self, parameters = [], returnVal=None):
        super(SZP1MethodCall, self).__init__(parameters, returnVal)
        self.methodName = 'SZP1'

class SZP2MethodCall(MethodCallStatement):
    def __init__(self, parameters = [], returnVal=None):
        super(SZP2MethodCall, self).__init__(parameters, returnVal)
        self.methodName = 'SZP2'

class AssignmentStatement(dataType.AbstractValue):
    def __init__(self):
        self.operator = AssignOperator()
    def __repr__(self):
        return "%s %s %s" % (self.left, self.operator, str(self.right))

    def push_expression(self,func_tree):
	exp = AST.assignment_expression()
	# configure left oprand
	if isinstance(self.left,GraphicsStateVariable):
	    exp.left_oprand = AST.terminal_expression("GS",self.left.identifier[3:len(self.left.identifier)-1])
	elif isinstance(self.left,str):
	    if self.left.startswith("GS"):
		if self.left.endswith(".all"):
		    exp.left_oprand = AST.terminal_expression("GS",self.left[3:len(self.left)-1-4])
		    exp.left_oprand.is_all = True
		else:
		    exp.left_oprand = AST.terminal_expression("GS",self.left[3:len(self.left)-1])
	    else:
	        exp.left_oprand = AST.terminal_expression("identifier",self.left)
	else:
	        exp.left_oprand = AST.terminal_expression("identifier",self.left.identifier)


	# configure right oprand
	if isinstance(self.right,Constant):
	    exp.right_oprand = AST.terminal_expression("int",self.right.value)

	elif isinstance(self.right,int):
	    exp.right_oprand = AST.terminal_expression("int",self.right)

	elif isinstance(self.right,BinaryExpression):
  	    exp.right_oprand = AST.binary_expression()
	    #exp.right_oprand.op = str(self.operator)
	    exp.right_oprand.oprand1 = AST.terminal_expression("identifier",self.right.left)
	    exp.right_oprand.oprand2 = AST.terminal_expression("identifier",self.right.right)
	    exp.right_oprand.op = str(self.right.operator)

	elif isinstance(self.right,UnaryExpression):
	    pass
	    exp.right_oprand = AST.unary_expression()
	    exp.right_oprand.op = str(self.right.operator)
	    exp.right_oprand.oprand = self.right.arg

	elif isinstance(self.right,Variable):

            if isinstance(self.right,GraphicsStateVariable):
                exp.right_oprand = AST.terminal_expression()
                exp.right_oprand.type = "GS"
                exp.right_oprand.value = self.right.identifier[3:len(self.right.identifier)-1]
	    else:
	        exp.right_oprand = AST.terminal_expression()
	        exp.right_oprand.type = "identifier"
	        exp.right_oprand.value = self.right.identifier

	elif isinstance(self.right,Boolean):
	    exp.right_oprand = AST.terminal_expression("bool",self.right.value)
 
        elif isinstance(self.right,dataType.RoundState_DTG):
            exp.right_oprand = AST.roundState_expression("RoundState_DTG")

        elif isinstance(self.right,dataType.RoundState_DG):
            exp.right_oprand = AST.roundState_expression("RoundState_DG")

	elif isinstance(self.right,dataType.RoundState_G):	
	    exp.right_oprand = AST.roundState_expression("RoundState_G")
        elif isinstance(self.right,dataType.RoundState_HG):
            exp.right_oprand = AST.roundState_expression("RoundState_HG")

        elif isinstance(self.right,dataType.RoundState_Super):
            exp.right_oprand = AST.roundState_expression("RoundState_Super")

        elif isinstance(self.right,dataType.RoundState_Super45):
            exp.right_oprand = AST.roundState_expression("RoundState_Super45")
		
        elif isinstance(self.right,ReadFromIndexedStorage):
	    exp.right_oprand = AST.IndexedStorage_expression()
	    exp.right_oprand.storage = self.right.storage
	    if isinstance(self.right.index,int):
	        exp.right_oprand.index_type = "int"
	        ind = AST.terminal_expression("int",self.right.index)
		exp.right_oprand.index = ind

	    elif isinstance(self.right.index,Variable):
	        exp.right_oprand.index_type = "identifier"
		ind = AST.terminal_expression("identifier",self.right.index.identifier)
	 	exp.right_oprand.index = ind
	    else:
		exp.right_oprand.index_type = "other type"	
	
	elif isinstance(self.right,dataType.PPEM_X):
	    exp.right_oprand = AST.terminal_expression()
	    exp.right_oprand.type = "MPPEM"
	    exp.right_oprand.value = "X"

	elif isinstance(self.right,dataType.PPEM_Y):
	    exp.right_oprand = AST.terminal_expression()
	    exp.right_oprand.type = "MPPEM"
	    exp.right_oprand.value = "Y"
	elif isinstance(self.right,dataType.PointSize):
	    exp.right_oprand = AST.terminal_expression()
	    exp.right_oprand.type = "PointSize"
	elif isinstance(self.right,MethodCallStatement):
	    exp.right_oprand = AST.methodCall_expression()
	    exp.right_oprand.methodName = self.right.methodName
	    exp.right_oprand.parameters = self.right.parameters
	else:
	    pass

	func_tree.push_expression(exp)
	


class OperationAssignmentStatement(AssignmentStatement):
    def __init__(self, variable, expression):
        super(OperationAssignmentStatement,self).__init__()
        self.left = variable
        self.right = expression

class CopyStatement(AssignmentStatement):
    def __init__(self, variable, data):
        super(CopyStatement,self).__init__()
        self.left = variable.identifier
	if hasattr(variable,'is_all'):
	    if variable.is_all:
		self.left = self.left + ".all"
        if variable.data == None or isinstance(data,GraphicsStateVariable):
	    self.right = data
  	else:	
            self.right = variable.data

class CallStatement(MethodCallStatement):
    def __init__(self, variable):
        super(CallStatement, self).__init__([variable])
        self.methodName = "CALL"
        self.call_rv = None
        self.repeats = None
        self.callee = variable
        self.call_args = None
	self.call_arg_list = []
	self.is_first = False
	self.stack_effect = 0
	self.function_tag = None


class LoopCallStatement(MethodCallStatement):
    def __init__(self, variable, count):
        super(LoopCallStatement, self).__init__([variable])
        self.count = count
        self.methodName = "LOOPCALL_"
	self.is_first = False
	self.call_args_list = []
    def __repr__(self):
        return "%s_%s" % (self.methodName, self.count)

class IndexedAssignment(AssignmentStatement):
    def __init__(self, index, var):
        self.index = index
        self.var = var
        self.storage = None
	self.unit = None
    def __repr__(self):
        return "%s[%s] := %s" % (self.storage, self.index, self.var)

    def push_expression(self,func_tree):
	exp = AST.assignment_expression()
	exp.left_oprand = AST.IndexedStorage_expression()
	exp.left_oprand.unit = self.unit
	exp.left_oprand.storage = self.storage
	exp.left_oprand.index = self.index.identifier
	exp.left_oprand.index_type = "identifier"
	exp.right_oprand = AST.terminal_expression("identifier",self.var.identifier)
	func_tree.push_expression(exp)

class WriteStorageStatement(IndexedAssignment):
    def __init__(self, index, var):
        super(WriteStorageStatement,self).__init__(index, var)
        self.storage = "storage_area"

class CVTStorageStatement(IndexedAssignment):
    def __init__(self, index, var):
        super(CVTStorageStatement,self).__init__(index, var)
        self.storage = "cvt_table"

class ReadFromIndexedStorage(AssignmentStatement):
    def __init__(self, storage, index):
        self.storage = storage
        self.index = index
    def __repr__(self):
        return "%s[%s]" % (self.storage, self.index)
    def eval(self, keep_abstract):
        if keep_abstract:
            return self
        ris = copy.copy(self)
        ris.index = ris.index.eval(keep_abstract)
        return ris

class EmptyStatement(object):
    def __repr__(self):
        return "NOP"

class ReturnStatement(object):
    def __repr__(self):
        return "RET"

    def push_expression(self,func_tree):
        exp = AST.expression()
	func_tree.push_expression(exp)


class JmpStatement(object):
    def __init__(self, dest):
        self.bytecode_dest = dest
        self.inst_dest = None
    def __repr__(self):
        return "JMPR %s" % (self.inst_dest)

class JROxStatement(object):
    def __init__(self, onTrue, e, dest):
        self.onTrue = onTrue
        self.e = e
        self.bytecode_dest = dest
        self.inst_dest = None
    def __repr__(self):
        op = 'JROT' if self.onTrue else 'JROF'
        d = "self" if self == self.inst_dest else str(self.inst_dest)
        return "%s (%s, %s)" % (op, self.e, d)

## in IfElseBlock, __str__ function is never been called,
## I will use this code to print the IR for if/else blocks
## I revised indent before If slightly





class LoopBlock(object):
    def __init__(self,condition = None,mode = 'TRUE',nesting_level = 1):
       self.condition = condition
       self.mode = mode
       self.loop_instructions = []
       self.else_instructions = []
       self.loop_ir = []
       self.else_ir = []
       self.nesting_level = nesting_level
       self.statement_id = None
    def __str__(self):
       c = self.condition.eval(True)
       if isinstance(c,dataType.UncertainValue):
           c = self.condition
       res_str = (self.nesting_level-1)*4*' '+'\n'
       #res_str += str(self.loop_ir[-1])+'\n'
       if self.mode == 'TRUE':
           res_str += (self.nesting_level-1)*4*' '+'while ( '+str(c)+' ) {\n'
       else:
	   res_str += (self.nesting_level-1)*4*' '+'while ( not '+str(c)+' ) {\n'
       for inst in self.loop_ir:
           if isinstance(inst,IfElseBlock):
                res_str += ((self.nesting_level) * 4 * ' ') + str(inst) + '\n'
           else:
                res_str += (self.nesting_level * 4 * ' ') + str(inst) + '\n'
       res_str += (self.nesting_level-1) * 4 * ' ' + '}\n'
       
       for inst in self.else_ir:
           if isinstance(inst,IfElseBlock):
                res_str += ((self.nesting_level) * 4 * ' ') + str(inst) + '\n'
           else:
                res_str += ((self.nesting_level-1) * 4 * ' ') + str(inst) + '\n'


       return res_str


class IfElseBlock(object):

    def push_expression(self,func_tree):
         exp = AST.if_expression()
	 func_tree.push_expression(exp)
	 func_tree.branch_stack.append(exp)
	 exp.reverse = self.reverse
	 self.func_tree = func_tree

    def __init__(self, condition = None, nesting_level = 1):
        self.reverse = False
        self.condition = condition
	self.func_tree = None
        # IR
        self.if_branch = []
        self.else_branch = []
        self.nesting_level = nesting_level

        # bytecode
        self.if_instructions = []
        self.else_instructions = []

        # random crap
        self.mode = 'THEN'
        self.jump_targets = {}
        
        # indicate if there is a break when
        # the if condition is not satisfied 
        self.break_indicator = False
        self.break_layer = 0

	# indicate if there is a return at the end
	# of if and else block
	self.rtn_if = False
	self.rtn_else = False

    def __str__(self):
        if self.reverse == True:
            tmp = self.if_branch
            self.if_branch = self.else_branch
            self.else_branch = tmp
        c = self.condition.eval(True)
        if isinstance(c, dataType.UncertainValue):
            c = self.condition
	
	if self.reverse:
	    res_str = (self.nesting_level-1)*4*' '+'if ( not '+str(c)+') {\n' 
	else:
	    res_str = (self.nesting_level-1)*4*' '+'if ('+str(c)+') {\n'
        if len(self.if_branch) == 0 and len(self.else_branch) > 0:
            res_str = (self.nesting_level-1)*4*' ' + 'if ( not '+str(c)+' ) {\n'
            for inst in self.else_branch:
		
		inst.push_expression(self.func_tree)
                if inst in self.jump_targets:
                    res_str += "%s:" % self.jump_targets[inst] + '\n'
                if hasattr(inst, 'jump_targets'):
                    inst.jump_targets = self.jump_targets
                res_str += (self.nesting_level * 4 * ' ') + str(inst) + '\n'
            res_str += (self.nesting_level-1) * 4 * ' ' + '}'

        else:
	    itr = 1
            for inst in self.if_branch:
		inst.push_expression(self.func_tree)
                if inst in self.jump_targets:
                    res_str += "%s:" % self.jump_targets[inst] + '\n'
                if hasattr(inst, 'jump_targets'):
                    inst.jump_targets = self.jump_targets
	        if isinstance(inst,IfElseBlock):
            	    res_str += ((self.nesting_level-1) * 4 * ' ') + str(inst) + '\n'
            #res_str += (self.nesting_level-1) * 4 * ' ' + '}'
	        else:
                    res_str += (self.nesting_level * 4 * ' ') + str(inst) + '\n'
            if self.rtn_if :
 	        res_str += (self.nesting_level * 4 * ' ') + 'RET' + '\n'
	    res_str += (self.nesting_level-1) * 4 * ' ' + '}'


            if len(self.else_branch) > 0:
		self.func_tree.branch_stack[-1].status = "ELSE"
                res_str += ' else {\n'
                for inst in self.else_branch:
		    inst.push_expression(self.func_tree)
                    if inst in self.jump_targets:
                        res_str += "%s:" % self.jump_targets[inst] + '\n'
                    if hasattr(inst, 'jump_targets'):
                        inst.jump_targets = self.jump_targets
                    res_str += (self.nesting_level * 4 * ' ') + str(inst) + '\n'
                if self.break_indicator:
                    res_str += (self.nesting_level * 4 * ' ') + 'break(' + str(self.break_layer) + ')\n'
                res_str += (self.nesting_level-1) * 4 * ' ' + '}'
	        if self.rtn_else :
                    res_str += (self.nesting_level * 4 * ' ') + 'RET' + '\n'
	    else:
		if self.break_indicator :
                    res_str += '\n' + ((self.nesting_level-1) * 4 * ' ') + 'break(' + str(self.break_layer) + ')\n'
        self.func_tree.branch_stack.pop()

        return res_str

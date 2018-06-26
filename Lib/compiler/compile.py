import sys
import os
import xml.etree.ElementTree as XML
import token
import AST
import bytecode

CURSOR_UP = '\x1b[1A'
ERASE = '\x1b[2K'

def generate_ttx(ori_ttx_file,out_ttx_file,font_bytecode):
    tree = XML.parse(ori_ttx_file)
    root = tree.getroot()
    for child_l1 in root:
        if child_l1.tag == 'fpgm':
            for child_l2 in child_l1:
                if child_l2.tag == 'assembly':
                    # access to the fpgm bytecode
                    string = '\n'
                    for fn in font_bytecode.fpgm.keys():
                        for line in font_bytecode.fpgm[fn]:
                            string = string + '      ' + line + '\n'
                    child_l2.text = string
        if child_l1.tag == 'prep':
            for child_l2 in child_l1:
                if child_l2.tag == 'assembly':
                    # access to prep bytecode
                    string = '\n'
                    for line in font_bytecode.prep:
                        string = string + '      ' + line + '\n'
                    child_l2.text = string
        if child_l1.tag == 'glyf':
            
            for child_l2 in child_l1:
                for child_l3 in child_l2:
                    if child_l3.tag == 'instructions':
                        for child_l4 in child_l3:
			    if child_l4.tag == 'assembly':
                                # access child_l2.attrib['name'] 's bytecode
			        string = '\n'
			        glyf_name = 'glyf.'+child_l2.attrib['name']
			        if glyf_name in font_bytecode.glyf.keys():
			            for line in font_bytecode.glyf[glyf_name]:
				        string = string + '      ' + line + '\n'
			            child_l4.text = string
    tree.write(out_ttx_file,encoding='utf-8',xml_declaration=True)


class compiler:


    class function:
        def __init__(self,t,n,c):
 	    self.function_type = t
	    self.function_name = n
            self.code = c


    # read a coi file,return a list of functions
    def read_coi(self,coi_file):
        with open(coi_file) as fd:
            buf = fd.readlines()
        lines = [x.strip() for x in buf]
    
        source_code_list = []
        temp = None
        for line in lines:
            if line == "####S":
 	        temp = []
	    elif line == "####E":
	        source_code_list.append(temp)
	        temp = None
	    else:
	        if not temp is None:
	            temp.append(line)
		


 	functions_code = []
	for source_code in source_code_list:
            if source_code[0].startswith("fpgm"):
		f_name = source_code[0][5:-2]
	        f = self.function("fpgm",f_name,source_code[1:])
		
      	    elif source_code[0].startswith("prep"):
		f = self.function("prep","prep",source_code[1:])
 
	    elif source_code[0].startswith("glyf"):
		f_name = source_code[0][5:-2]
		f = self.function("glyf",f_name,source_code[1:])
	    functions_code.append(f)
	return functions_code



    def lexical_analysis(self,source_code):

	def process_line(string):
	    elements = []
	    buf = ""
	    string = string.replace(',',' ')
	    for char in string:
	        if char == ' ':
		    if len(buf)>0:
		        elements.append(buf)
		        buf = ""
		elif char in ['(',')','[',']','{','}']:
		    if len(buf)>0:
			elements.append(buf)
			buf = ""
	 	    elements.append(char)
		else:
		    buf += char
	    if len(buf)>0:
		elements.append(buf)

	    return elements


        token_list = []
        for line in source_code:
	    line.replace(',','')
            elements = process_line(line)
            tokens = []
	    for e in elements:
	 	t = token.get_token(e)
                tokens.append(t)
            token_list.append(tokens)
        return token_list



    # compile a coi file
    #def compile(self,coi_file):
        # read the source code 
    #    functions = self.read_coi(coi_file)
    #    bp = bytecode.bytecode_producer()
    #    for f in functions:
    #        token_list = self.lexical_analysis(f.code)
    #        func_AST = AST.construct_AST(token_list)
    #        bp.generate_code(func_AST)

    def __init__(self):
	pass

    def compile(self,ast):
	print '---------------- coi code created. compiling ... '
	bp = bytecode.bytecode_producer()

        for f in ast.program_functions:
	    print 'fpgm:',f.function_num
	    f.arguments = ast.fpgm2args[f.function_num]
	    f.stack_effect = ast.fpgm2stack_effect[f.function_num]
	    bp.generate_code(f)
	    
        if not ast.prep_function is None:
	    print 'prep'
	    bp.generate_code(ast.prep_function) 

	for f in ast.glyph_functions:
	    bp.generate_code(f)

	sys.stdout.write(CURSOR_UP)
	sys.stdout.write(ERASE)
	if not ast.output_dir is None:
	    temp = ast.font_name.split('/')
	    filename = temp[-1]
	    filename = temp[-1][:-4] + '_modified.ttx'
	    modified_file_name = ast.output_dir+filename
	    generate_ttx(ast.font_name,modified_file_name,bp.get_bytecode())
	    print '**************** modified ttx file created'




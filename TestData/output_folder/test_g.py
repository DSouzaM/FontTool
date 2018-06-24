import sys
import os
import xml.etree.ElementTree as XML



tree_ori = XML.parse("arial.ttx")
tree_mod = XML.parse("arial_modified.ttx")

root_ori = tree_ori.getroot()
root_mod = tree_mod.getroot()

test_list = []
itr = 0
bound = int(sys.argv[1])
glyph_func = {}
for child_l1 in root_ori:
        if child_l1.tag == 'glyf':

            for child_l2 in child_l1:
                for child_l3 in child_l2:
                    if child_l3.tag == 'instructions':
                        for child_l4 in child_l3:
                            if child_l4.tag == 'assembly':
                                # access child_l2.attrib['name'] 's bytecode
                                glyf_name = child_l2.attrib['name']
				glyph_func[glyf_name] = child_l4.text
				if itr < bound:
				    test_list.append(glyf_name)
				    itr += 1

for child_l1 in root_mod:
        if child_l1.tag == 'glyf':

            for child_l2 in child_l1:
                for child_l3 in child_l2:
                    if child_l3.tag == 'instructions':
                        for child_l4 in child_l3:
                            if child_l4.tag == 'assembly':
                                # access child_l2.attrib['name'] 's bytecode
                                glyf_name = child_l2.attrib['name']
                                if glyf_name in test_list:
				    child_l4.text = glyph_func[glyf_name]

print test_list
tree_mod.write("text.ttx",encoding='utf-8',xml_declaration=True)
os.system("ttx -q text.ttx")
os.system("./a.out")
os.system("rm text.tt*")

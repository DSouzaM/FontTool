import os
import os.path
import sys
import time
import psutil
import fontTools.analysis as FT
from threading import Thread
from threading import Event
from multiprocessing import Process
from multiprocessing import Value
import thread
CURSOR_UP = '\x1b[1A'
ERASE = '\x1b[2K'

print 'pyftanalysis test script:'
input_directory = "./"
output_directory = "./output_folder"
is_default_output_dir = False

# get input directory, the input directory has to be existed
# default input directory is the current working dir ./
while True:
    string = raw_input('---------------- input directory(press enter for default) >')
    if string == "":
	sys.stdout.write(CURSOR_UP)
        sys.stdout.write(ERASE)
        print '**************** default input directory(current)'
	break
    else:
        if not os.path.exists(string):
            sys.stdout.write(CURSOR_UP)
            sys.stdout.write(ERASE)
            raw_input('**************** input directory does to exist,press any key to re-enter >')
            sys.stdout.write(CURSOR_UP)
            sys.stdout.write(ERASE)
        else:
            sys.stdout.write(CURSOR_UP)
            sys.stdout.write(ERASE)
            print '**************** input directory:',string
            input_directory = string
            break
        
# get output directory, the output directory has to be existed
# default output directory is ./output_folder, will create if it does not exist(only auto create deafult dir)
while True:
    string = raw_input('---------------- output directory(press enter for default) >')
    if string == "":
        sys.stdout.write(CURSOR_UP)
        sys.stdout.write(ERASE)
        print '**************** default output directory(',output_directory,')'
	is_default_output_dir = True
	break
    else:
        if not os.path.exists(string):
            sys.stdout.write(CURSOR_UP)
            sys.stdout.write(ERASE)
            raw_input('**************** input directory does to exist,press any key to re-enter >')
	    sys.stdout.write(CURSOR_UP)
	    sys.stdout.write(ERASE)
	else:
            sys.stdout.write(CURSOR_UP)
            sys.stdout.write(ERASE)
	    print '**************** input directory:',string
	    output_directory = string
	    break

# create default dir if it does not exist
if is_default_output_dir:
    if not os.path.exists(output_directory):
        os.mkdir(output_directory)


print '---------------- walking through the input directory...'
# walk through the tree of input directory, get all font files
directory_fonts = []
for root, dirs, files in os.walk(input_directory):
    if not root == output_directory and len(files)>0:
	font_list = []
	for filename in files:
	    if filename.endswith(".ttx"):
                font_list.append(filename)
        if len(font_list) > 0:
   	    directory_fonts.append((root,font_list))

# 'directory_fonts' is a list of pairs,whose first element is the directory and
# second element is a list of the font files in the corresponding directory
count = 0
for directory in directory_fonts:
    count += len(directory[1])

# print the font files to test
print "----------------", count ,"fonts are found."
itr = 1
fonts = []
fonts_without_dir = []
for d in directory_fonts:
    print '**************** in directory:  <',d[0],'>'
    for font_name in d[1]:
        print '# ',itr,'. ',font_name
	fonts_without_dir.append(font_name)
	fonts.append(d[0]+'/'+font_name)
	itr += 1
print '\n\n---------------- press  s  to start testing.'
print '---------------- press  q  to quit the program.\n'
while True:
    key_press = raw_input("> ")
    if key_press == 's':
        break
    elif key_press == 'q':
	sys.stdout.write(CURSOR_UP)
        sys.stdout.write(ERASE)
	print '---------------- quit'
        sys.exit()
    else:
        sys.stdout.write(CURSOR_UP)
        sys.stdout.write(ERASE)

sys.stdout.write(CURSOR_UP)
sys.stdout.write(ERASE)
sys.stdout.write(CURSOR_UP)
sys.stdout.write(ERASE)
sys.stdout.write(CURSOR_UP)
sys.stdout.write(ERASE)
sys.stdout.write(CURSOR_UP)
sys.stdout.write(ERASE)


print '---------------- start testing ...'

def erase_lines(n):
    for i in range(0,n):
        sys.stdout.write(CURSOR_UP)
	sys.stdout.write(ERASE)

num_of_success = 0
# for each font
for i in range (0,len(fonts)):
    # figure out file directories
    current_font_name = fonts_without_dir[i]
    output_coi_dir = output_directory+"/"+current_font_name[:-4]+".coi"
    output_ttx_dir = output_directory+"/"+current_font_name[:-4]+"_modified.ttx"
    output_ttf_dir = output_directory+"/"+current_font_name[:-4]+"_modified.ttf"
    ori_ttx_dir = output_directory+"/"+current_font_name[:-4]+".ttx"
    ori_ttf_dir = output_directory+"/"+current_font_name[:-4]+".ttf"    
    
    # remove output files if existed
    if os.path.isfile(output_coi_dir):
        os.system("rm "+output_coi_dir)
    if os.path.isfile(output_ttx_dir):
        os.system("rm "+output_ttx_dir)
    if os.path.isfile(output_ttf_dir):
        os.system("rm "+output_ttf_dir)

    # symbolic execute input ttx file 
    args = ['-fipGz',fonts[i],output_coi_dir]
    print '**************** symbolic executing ',fonts[i]
    FT.test(args)
    print '**************** creating .ttf file...'

    cmd = "ttx -q "+output_directory+'/'+current_font_name[:-4]+"_modified.ttx"
    os.system(cmd)
    erase_lines(1)
    print '**************** .ttf file created.'

    # make a copy of .ttx and .ttf file of original font file in output directory
    cmd_create_ori_ttx = "cp "+input_directory+'/'+current_font_name[:-4]+".ttx"+' '+output_directory+'/'+current_font_name[:-4]+".ttx"
    cmd_create_ori_ttf = "ttx -q "+output_directory+'/'+current_font_name[:-4]+".ttx"
    if not os.path.isfile(output_directory+'/'+current_font_name[:-4]+".ttx"):
        os.system(cmd_create_ori_ttx)
    if not os.path.isfile(output_directory+'/'+current_font_name[:-4]+".ttf"):
        os.system(cmd_create_ori_ttf)



    # running bitmap matching test with FreeType2 #
    print '**************** running bitmap matching test...'    
    cmd = output_directory+'/'+'freetype2_test '+ori_ttf_dir+' '+output_ttf_dir
    os.system(cmd)
    print current_font_name + ' done!'
    print '-----------------------------------------------------------------'
    num_of_success += 1
     

print "done! ",num_of_success,"/",count,"success"









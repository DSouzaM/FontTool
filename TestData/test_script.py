import os
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
for i in range (0,len(fonts)):
    current_font_name = fonts_without_dir[i]
    output_name = output_directory+"/"+current_font_name[:-4]+".coi"
    args = ['-fipGz',fonts[i],output_name]
    print '**************** symbolic executing ',fonts[i]
    FT.test(args)

    print '**************** creating .ttf file ...'
    cmd = "ttx -q "+output_directory+'/'+current_font_name[:-4]+"_modified.ttx"
    os.system(cmd)
    erase_lines(1)
    print '**************** .ttf file created.'
    print '**************** running bitmap matching test ...'
    
    bitmap_input = output_directory+'/'+current_font_name[:-4]+".ttf"
    bitmap_output = output_directory+'/'+current_font_name[:-4]+"_modified.ttf"
    cmd = output_directory+'/'+'a.out '+bitmap_input+' '+bitmap_output
    os.system(cmd)


    num_of_success += 1
     

print "done! ",num_of_success,"/",count,"success"









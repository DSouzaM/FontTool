"""
usage: pyftanalysis [options] inputfile

    pyftanalysis %s -- TrueType Bytecode Analysis Tool

    General options:
    -h Help: print this message
    -i IR: print out IR rather than bytecode
    -s State: print the graphics state after executing prep
    -c CallGraph: print out the call graph
    -m MaxStackDepth: print out the maximum stack depth for the executed code
    -p Prep: print out prep bytecodes/IR
    -f Functions: print out function bytecodes/IR
    -z Glyphs: print out selected glyph bytecode/IR
    -g NAME Glyph: execute prep plus hints for glyph NAME
    -G AllGlyphs: execute prep plus hints for all glyphs in font
    -r Reduce: remove uncalled functions (tree shaking)
    -x XML: produce ttx instead of ttf output (for -r)
    --cvt CVT: print the CVT after executing prep
    -v Verbose: be more verbose
"""
from __future__ import print_function, division, absolute_import
import time
import psutil
import tempfile
import copy
import logging
import pdb
import math
import getopt
import os
import sys
from fontTools.ttLib.compiler import compile, ast
from fontTools.ttLib import TTFont
from fontTools.ttLib.bytecodeContainer import BytecodeContainer
from fontTools.ttLib.instructions import statements, abstractExecute, IntermediateCode
from fontTools.ttLib.data import dataType
from fontTools.misc.util import makeOutputFileName


CURSOR_UP = '\x1b[1A'
ERASE = '\x1b[2K'


def ttDump(input):
    output = tempfile.TemporaryFile(suffix=".ttx")
    ttf = TTFont(input, 0, allowVID=False,
                 quiet=None, ignoreDecompileErrors=True,
                 fontNumber=-1)
    ttf.saveXML(output, tables=[],
                skipTables=[], splitTables=False,
                disassembleInstructions=True,
                bitmapGlyphDataFormat='raw')
    ttf.close()
    return output


def executeGlyphs(abstractExecutor, initialEnvironment, glyphs):
    process = psutil.Process(os.getpid())
    called_functions = set()
    i = 0
    for glyph in glyphs:
        #i += 1
        # if  i>50:
        #   continue
        abstractExecutor.glyph_num += 1
        abstractExecutor.environment = copy.deepcopy(initialEnvironment)
        abstractExecutor.execute(glyph)
        called_functions.update(list(set(abstractExecutor.visited_functions)))

    return called_functions


def analysis(bytecodeContainer, glyphs, font_name):
    abstractExecutor = abstractExecute.Executor(bytecodeContainer)
    abstractExecutor.all_glyphs = len(glyphs)
    abstractExecutor.current_font_name = font_name
    abstractExecutor.start_time = time.time()
    called_functions = set()
    # for key in bytecodeContainer.function_table.keys():
    #	if len(bytecodeContainer.function_table[key].body.instructions)>0:
    #	    print (bytecodeContainer.function_table[key].body.instructions[0].id,key)
    #	    print (bytecodeContainer.function_table[key].body.instructions,'\n')
    # sys.exit()

    if 'prep' in bytecodeContainer.tag_to_programs:
        #print('executing prep...\n')
        abstractExecutor.execute('prep')
        called_functions.update(list(set(abstractExecutor.visited_functions)))
    # NB: if there's no prep we don't explicitly output the initial graphics state

    environment_after_prep = abstractExecutor.environment
    called_functions.update(executeGlyphs(
        abstractExecutor, environment_after_prep, glyphs))
    return abstractExecutor, called_functions


class Options(object):
    verbose = False
    outputState = False
    outputCVT = False
    outputIR = False
    outputPrep = False
    outputFunctions = False
    outputGlyfPrograms = False
    outputCallGraph = False
    outputMaxStackDepth = False
    outputXML = False
    glyphs = []
    allGlyphs = False
    reduceFunctions = False

    def __init__(self, rawOptions, numFiles):
        for option, value in rawOptions:
            # general options
            if option == "-h":
                from fontTools import version
                print(__doc__ % version)
                sys.exit(0)
            elif option == "-i":
                self.outputIR = True
            elif option == "-s":
                self.outputState = True
            elif option == "--cvt":
                self.outputCVT = True
            elif option == "-c":
                self.outputCallGraph = True
            elif option == "-m":
                self.outputMaxStackDepth = True
            elif option == "-p":
                self.outputPrep = True
            elif option == "-f":
                self.outputFunctions = True
            elif option == "-z":
                self.outputGlyfPrograms = True
            elif option == "-g":
                self.glyphs.append(value)
            elif option == "-G":
                self.allGlyphs = True
            elif option == "-v":
                self.verbose = True
            elif option == "-r":
                self.reduceFunctions = True
            elif option == "-x":
                self.outputXML = True

        if (self.verbose):
            logging.basicConfig(level=logging.INFO)
        else:
            logging.basicConfig(level=logging.ERROR)


def usage():
    from fontTools import version
    print(__doc__ % version)
    sys.exit(2)


def fd_print(fd, string):
    if not fd is None:
        fd.write(string+"\n")
    else:
        print(string)


def process(jobs, options):
    for (input, origin, output) in jobs:
        font_ast = ast.font_AST()
        font_ast.font_name = input
        if not output is None:
            temp = output.split('/')
            # get output dir with output .coi filename
            output_dir = ""
            for k in range(0, len(temp)-1):
                output_dir = output_dir + temp[k] + '/'
            font_ast.output_dir = output_dir

        tt = TTFont()
        tt.importXML(input, quiet=None)
        bc = BytecodeContainer(tt)

        if (options.allGlyphs):
            glyphs = filter(lambda x: x != 'fpgm' and x !=
                            'prep', bc.tag_to_programs.keys())
        else:
            glyphs = map(lambda x: 'glyf.'+x, options.glyphs)

        first_time_call_args = {}
        if options.outputIR or options.reduceFunctions:
            ae, called_functions = analysis(bc, glyphs, input)
            # configure call args of fpgm
            first_time_call_args = ae.first_time_call_args
            first_time_stack_effect = ae.first_time_stack_effect
            for k in first_time_call_args.keys():
                font_ast.add_fpgm_args(
                    k, first_time_call_args[k], first_time_stack_effect[k])

        output_fd = None
        if not output is None:
            output_fd = open(output, "w")

        if (options.outputPrep):
            fd_print(output_fd, "PREP:")
            if (options.outputIR):
                if 'prep' in bc.tag_to_programs:
                    # create function tree for compiler
                    prep_ast = ast.function()
                    prep_ast.font_ast = font_ast
                    prep_ast.function_type = "prep"
                    font_ast.prep_function = prep_ast
                    bc.print_IR(prep_ast, output_fd, bc.IRs['prep'])
                else:
                    fd_print(output_fd, "  <no prep>")
            else:
                bc.tag_to_programs['prep'].body.pretty_print()
            fd_print(output_fd, "")

        if (options.outputFunctions):
            for key, value in bc.function_table.items():
                fd_print(output_fd, "Function #%d" % (key))
                if (options.outputIR):
                    tag = "fpgm_%s" % key
                    if tag in bc.IRs:
                        # create function tree for compiler
                        fpgm_ast = ast.function()
                        fpgm_ast.font_ast = font_ast
                        fpgm_ast.function_type = "fpgm"
                        fpgm_ast.function_num = key
                        font_ast.program_functions.append(fpgm_ast)
                        bc.print_IR(fpgm_ast, output_fd, bc.IRs[tag])
                    else:
                        fd_print(output_fd, "  <not executed, no IR>")
                else:
                    value.body.pretty_print()     #

                fd_print(output_fd, "")

        if (options.outputGlyfPrograms):
            for glyph in bc.IRs.keys():
                if not glyph.startswith('glyf'):
                    continue
                fd_print(output_fd, "%s:" % glyph)
                if (options.outputIR):
                    # create function tree for compiler
                    glyf_ast = ast.function()
                    glyf_ast.font_ast = font_ast
                    glyf_ast.function_type = "glyf"
                    glyf_ast.function_tag = glyph
                    font_ast.glyph_functions.append(glyf_ast)
                    bc.print_IR(glyf_ast, output_fd, bc.IRs[glyph])
                else:
                    bc.tag_to_programs[glyph].body.pretty_print()
                fd_print(output_fd, "")

        if (options.outputCallGraph):
            fd_print(output_fd, "called function set:")
            fd_print(output_fd, called_functions)
            fd_print(output_fd, "call graph (function, # calls to):")
            for item in ae.global_function_table.items():
                fd_print(output_fd, item)

        if (options.outputState):
            ae.environment.pretty_print(output_fd)
        if (options.outputCVT):
            fd_print(output_fd, "CVT = "+ae.environment.cvt)
        if (options.outputMaxStackDepth):
            fd_print(output_fd, "Max Stack Depth =", ae.maximum_stack_depth)
        if (options.reduceFunctions):
            function_set = bc.function_table.keys()
            unused_functions = [
                item for item in function_set if item not in called_functions]

            bc.removeFunctions(unused_functions)
            bc.updateTTFont(tt)
            output = os.path.join(os.path.dirname(
                origin), "Reduced%s" % os.path.basename(origin))
            if (options.outputXML):
                output = makeOutputFileName(output, ".ttx")
                tt.saveXML(output)
            else:
                output = makeOutputFileName(output, ".ttf")
                tt.save(output)
        if type(input) is file:
            input.close()

        # close output fd
        if not output_fd is None:
            output_fd.close()

        c = compile.compiler()
        c.compile(font_ast)


def parseOptions(args):
    try:
        rawOptions, filenames = getopt.getopt(args, "hiscpfzGmg:vrx", ['cvt'])
        files = []
        output_files = []
        output_dir = None
        for name in filenames:
            if name.endswith(".coi"):
                output_files.append(name)
            else:
                files.append(name)

    except getopt.GetoptError:
        usage()

    if not files:
        usage()

    options = Options(rawOptions, len(files))
    jobs = []

    if not len(files) == len(output_files):
        output_files = None

    for i in range(0, len(files)):
        input = files[i]
        fileformat = input.split('.')[-1]
        if fileformat == 'ttf':
            output = ttDump(input)
            output.seek(0)
            if output_files == None:
                jobs.append((output, input, None))
            else:
                jobs.append((output, input, output_files[i]))
        elif fileformat == 'ttx':
            if output_files == None:
                jobs.append((input, input, None))
            else:
                jobs.append((input, input, output_files[i]))
        else:
            raise NotImplementedError
    return jobs, options


def main(args=None):
    if args is None:
        args = sys.argv[1:]
    jobs, options = parseOptions(args)
    process(jobs, options)


def test(args):
    jobs, options = parseOptions(args)
    process(jobs, options)


if __name__ == "__main__":
    main(sys.argv[1:])

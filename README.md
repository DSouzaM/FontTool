### pyftanalysis

This repository was forked some time ago from the main [fonttools project](https://github.com/fonttools/fonttools/). It introduces static analysis to the hinting language used in TrueType fonts. This README provides some background, but for a more thorough explanation of the project's motivation, implementation, and challenges, consult the [original paper](https://uwspace.uwaterloo.ca/handle/10012/9116).

### Background

#### TrueType and the role of bytecode

Apple's [TrueType Reference Manual](https://developer.apple.com/fonts/TrueType-Reference-Manual/) is an invaluable resource for understanding how TrueType fonts work.

TrueType fonts are *outline fonts*: they describe glyphs in terms of [mathematical contours](https://developer.apple.com/fonts/TrueType-Reference-Manual/RM01/Chap1.html#contours), and when a font is rendered, these contours are superimposed onto a grid of pixels and filled in. With this strategy, fonts can scale to different resolutions relatively easily (in contrast to *bitmap fonts*).

However, it is still possible to produce [anomalous results](https://developer.apple.com/fonts/TrueType-Reference-Manual/RM03/Chap3.html#rasterization) at different resolutions, since floating point curves cannot be perfectly mapped to discrete points. The TrueType specification includes a low-level [stack-based bytecode](https://developer.apple.com/fonts/TrueType-Reference-Manual/RM05/Chap5.html) which allows font designers to programmatically correct these anomalies (this process is called *hinting*).

#### Static analysis on bytecode

TrueType bytecode is challenging to reason about, especially because it is highly dynamic and stack-based. For example, the target of a function call is not stated explicitly, but determined by the value at the top of the stack when a `CALL` instruction is executed. Since all communication occurs through the stack, both the number of parameters and the number of return values are also implicit.

Minimizing font size is beneficial to reduce web page load times and Internet data usage. Developers already use font subsetting to remove unused glyphs from their font files (fonttools provides a [module for subsetting](https://github.com/fonttools/fonttools/tree/master/Lib/fontTools/subset)). Static analysis could provide room for further optimizations:

- Dead/no-effect code elimination: Most hinting for fonts is auto-generated by font programs. The generate code often has helper functions which never get executed. There are also instructions which we can statically reason to have no effect on execution.

  - In the presence of font subsetting, this effect is likely exacerbated, since it does not make any changes to the font's bytecode.

- Font specialization: Since hinting is a means to correct for rasterization anomalies at extreme screen resolutions, we speculate that a portion of bytecode could be removed if we specialize the code for a particular resolution.

### Development

#### Setup

Run the following bash commands to get started:
```
# use of a virtualenv is recommended
VENV_DIR='enter a location here'
virtualenv --python=python2.7 $VENV_DIR
source $VENV_DIR/bin/activate

# create the `pyftanalysis` executable
python setup.py develop

# dependencies for the tool
pip install psutil
```

#### Running the tool

`pyftanalysis -h` will print all input options. Below are some useful commands.

```
# Run analysis on the TestData/Filxgirl.ttx font, writing the IR of the
# prep, fpgm, and glyf programs to out.coi:
pyftanalysis -ifpzG TestData/Filxgirl.ttx out.coi

# Run analysis on the TestData/Filxgirl.ttx font, removing unused function
# from fpgm, outputting the result to TestData/ReducedFilxGirl.ttf:
pyftanalysis -fpGzr TestData/Filxgirl.ttx

# pyftanalysis only operates on ttf files. The following will convert a
# ttf file (binary) to ttx file (human-readable XML):
ttx TestData/Filxgirl.ttf
```

#### Development workflow

By running `python setup.py develop` during setup, changes take effect immediately after files are saved.

There are a few locations you'll find most of the code contributed by this project:

- [Lib/fontTools/analysis.py](../Lib/fontTools/analysis.py): entry-point to the utility

- [Lib/fontTools/ttLib/compiler](../Lib/fontTools/ttLib/compiler), [Lib/fontTools/ttLib/instructions](../Lib/fontTools/ttLib/instructions): modules implementing most of the analysis logic

- [TestData](../TestData): folder with various `.ttf` and `.ttx` files for testing the tool (somewhat disorganized)

#### Current status / Next steps

The tool works on small font files, but tends to crash on more complex files (especially those containing relative jump instructions). This makes it difficult to use to validate new ideas (like font specialization, mentioned earlier). Some work could be done to improve this:

- Refactoring code: Some of the code, particularly [Lib/fontTools/ttLib/instructions/abstractExecute.py](../Lib/fontTools/ttLib/instructions/abstractExecute.py), is monolithic and difficult to reason about. Refactoring this code (perhaps into smaller modules) would make it much easier to reason about and fix bugs.

- Documentation: The code appears to have certain invariants/assumptions about the bytecode it runs on. For example, the successors to an `IF` instruction seem to be the if-branch, an `ELSE` instruction (if any), and the ending `EIF` instruction. Invariantas like these are not explicitly documented, but recovering these and documenting them would be very helpful in understanding the code.

- Test automation: Currently, it's hard to be confident about the correctness of any changes made to the codebase, beyond running on sample files (and maybe verifying that the font looks the same). [TestData/output_folder/test/test.c](../TestData/output_folder/test/test.c) compares the bitmaps of rendered fonts at a given resolution, so this could be a good start.

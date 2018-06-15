from subprocess import call
import glob

directory = "/usr/share/fonts/truetype/msttcorefonts/"
ttfs = glob.glob(directory + "*.ttf")

for ttf in ttfs:
    
    call(["pyftanalysis", "-fips" , ttf])






import sys
import freetype

def render_and_compare(font1, font2):
    face1 = freetype.Face(font1)
    face2 = freetype.Face(font2)

    face1_chars = list(face1.get_chars())
    face2_chars = list(face2.get_chars())

    if face1_chars != face2_chars:
        print "Error: character sets are different"
        return False

    # Try to sample a few different screen resolutions
    resolutions = [50, 250, 450]


    for resolution in resolutions:
        errors = 0
        print "Comparing fonts at %d dpi" % resolution
        face1.set_char_size(50*64, 0, resolution, 0)
        face2.set_char_size(50*64, 0, resolution, 0)
        for _, glyph_index in face1_chars:
            face1.load_glyph(glyph_index)
            face2.load_glyph(glyph_index)

            if face1.glyph.bitmap.buffer != face2.glyph.bitmap.buffer:
                print "Error: Difference detected for glyph %d" % glyph_index
                errors += 1
        if errors:
            print "Errors for %d/%d glyphs" % (errors, len(face1_chars))
            return False

    # If no errors detected, assume success
    print "No discrepancies detected between fonts"
    return True

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print "Usage: python %s ttf_file_1 ttf_file_2" % sys.argv[0]
        sys.exit(1)
    sys.exit(not render_and_compare(sys.argv[1], sys.argv[2]))
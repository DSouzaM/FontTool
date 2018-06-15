#include <ft2build.h>
#include FT_FREETYPE_H



int main()
{
    int error;
    // initialize truetype2 lib
    FT_Library library;
    error = FT_Init_FreeType(&library);
    if(error)
    {
	printf("error initializing freetype2 lib:%d\n",error);
    }
    printf("freetype2 initialized.\n");

    
    // load the font face 
    FT_Face face;
    error = FT_New_Face(library,"./arial.ttf",0,&face);
    if(error || &face == NULL)
    {
        printf("error loading font face:%d\n",error);

    }
    printf("font face loaded.\n");
    printf("num of glyphs:%ld\n",face->num_glyphs);

    error = FT_Set_Char_Size(
              face,    /* handle to face object           */
              50 * 64, /* char_width in 1/64th of points  */
              0,       /* char_height in 1/64th of points */
              100,     /* horizontal device resolution    */
              0 );     /* vertical device resolution      */
    //error = FT_Set_Pixel_Sizes(
    //          face,   /* handle to face object */
    //          0,      /* pixel_width           */
    //          16 );   /* pixel_height          */
    // test: get the index of first character
    FT_UInt index;
    FT_ULong character = FT_Get_First_Char(face,&index);
    error = FT_Load_Char(face,3,FT_LOAD_DEFAULT);
    int itr = 0;
    while(1)
    {
        itr += 1;
        character = FT_Get_Next_Char(face,character,&index);
        if(!index)
            break;
    }
    error = FT_Render_Glyph(face->glyph,FT_RENDER_MODE_MONO);
    printf("%d,%d\n",face->glyph->bitmap.rows,face->glyph->bitmap.width);   
    printf("%ld\n",sizeof(face->glyph->bitmap.buffer));
    for(int i=0;i<face->glyph->bitmap.rows;i++){
        for(int j=0;j<face->glyph->bitmap.width;j++){
            printf("(%d,%d):%d\n",i,j,face->glyph->bitmap.buffer[i*face->glyph->bitmap.width+j]);

        }
    }
 
    return 0;
}


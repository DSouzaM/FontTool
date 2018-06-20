#include <stdio.h>
#include <string.h>
#include <ft2build.h>
#include FT_FREETYPE_H

struct Glyf
{
    FT_UInt index;
    FT_ULong character;
    FT_Bitmap* bitmap;

};


struct Font
{
    char* font_name;
    int num_of_glyf;
    struct Glyf** glyphs; 

};


void compare(struct Font* f1,struct Font* f2)
{
    for(int k=0;k<1;k++)
    {
      struct Glyf* g1 = f1->glyphs[k];
      struct Glyf* g2 = f2->glyphs[k];  
     
      int width1 = g1->bitmap->rows;
      int height1 = g1->bitmap->width;

      int width2 = g2->bitmap->rows;
      int height2 = g2->bitmap->width;
   
      printf("%d,%d\n",g1->index,g2->index);
      printf("%ld,%ld\n",g1->character,g2->character);
      printf("%d,%d\n",width1,width2);
      printf("%d,%d\n\n",height1,height2);
      for(int i=0;i<width1*height1;i++)
      	printf("%d,%d\n",g1->bitmap->buffer[i],g2->bitmap->buffer[i]);

      
    }


 
}


struct Font* load_font(char* filename)
{
    struct Font *f = (struct Font*)malloc(sizeof(struct Font));
    f->font_name = filename;
    int error;
    FT_Library library;
    error = FT_Init_FreeType(&library);
    if(error)
    {
        printf("error initializing freetype2 lib:%d\n",error);
    }
    printf("freetype2 initialized.\n");


    // load the font face 
    FT_Face face;
    error = FT_New_Face(library,filename,0,&face);
    if(error || &face == NULL)
    {
        printf("error loading font face:%d\n",error);

    }
    printf("font face loaded.\n");
    printf("num of glyphs:%ld\n",face->num_glyphs);
    f->glyphs = (struct Glyf**)malloc(sizeof(struct Glyph*)*(face->num_glyphs));
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
    FT_GlyphSlot glyf = face->glyph;
    int itr = 0;
    while(1)
    {
        error = FT_Load_Char(face,index,FT_LOAD_DEFAULT);
 	error = FT_Render_Glyph(glyf,FT_RENDER_MODE_NORMAL);
	struct Glyf* g = (struct Glyf*)malloc(sizeof(struct Glyf));
        g->index = index;
        g->character = character;
	g->bitmap = (FT_Bitmap*)malloc(sizeof(FT_Bitmap));
	memcpy(g->bitmap,&(glyf->bitmap),sizeof(FT_Bitmap));	
	f->glyphs[itr] = g;
	character = FT_Get_Next_Char(face,character,&index);
	itr += 1;
        //for(int k=0;k<g->bitmap->rows*g->bitmap->width;k++)
	//    printf("%d\n",g->bitmap->buffer[k]);
	break;
	if(!index)
	    break;

    }
   
    
 
    FT_Done_Face(face);
    FT_Done_FreeType(library);
    f->num_of_glyf = itr;
    return f;
}


int main()
{
    int error;
    printf("arial\n");
    struct Font* f1 = load_font("arial.ttf");
    printf("arial modified\n");
    struct Font* f2 = load_font("arial_modified.ttf");
    compare(f1,f2);
    return 0;
}

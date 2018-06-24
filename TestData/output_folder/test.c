#include <stdio.h>
#include <string.h>
#include <ft2build.h>
#include FT_FREETYPE_H

int main(int argC,char* argV[]){
    
    char* ori_filename = "arial.ttf";
    char* mod_filename = "arial_modified.ttf";
    if(argC==3)
    {
        ori_filename = argV[1];    
        mod_filename = argV[2];
    }

    int error;
    FT_Library library;
    error = FT_Init_FreeType(&library);
    //printf("error:%d\n",error);

    // load the original font face 
    FT_Face face1;
    error = FT_New_Face(library,ori_filename,0,&face1);

    //printf("error:%d\n",error);


    // load the modified font face 
    FT_Face face2;
    error = FT_New_Face(library,mod_filename,0,&face2);
    //printf("error:%d\n",error);

    // set font size for ori and mod font face
    error = FT_Set_Char_Size(
              face1,    /* handle to face object           */
              50 * 64, /* char_width in 1/64th of points  */
              0,       /* char_height in 1/64th of points */
              100,     /* horizontal device resolution    */
              0 );     /* vertical device resolution      */
    //error = FT_Set_Pixel_Sizes(
    //          face,   /* handle to face object */
    //          0,      /* pixel_width           */
    //          16 );   /* pixel_height          */
    // test: get the index of first character

    //printf("error:%d\n",error);
 
    error = FT_Set_Char_Size(
              face2,    /* handle to face object           */
              50 * 64, /* char_width in 1/64th of points  */
              0,       /* char_height in 1/64th of points */
              100,     /* horizontal device resolution    */
              0 );     /* vertical device resolution      */
    //error = FT_Set_Pixel_Sizes(
    //          face,   /* handle to face object */
    //          0,      /* pixel_width           */
    //          16 );   /* pixel_height          */
    // test: get the index of first character
    //printf("error:%d\n",error);


    FT_UInt index;
    FT_ULong character = FT_Get_First_Char(face1,&index);
    FT_GlyphSlot glyf1 = face1->glyph;
    FT_GlyphSlot glyf2 = face2->glyph;
    int itr=0;
    int num_of_not_same = 0;
    while(1)
    {
 	itr += 1;
	//printf("glyph #%d\n",itr);
        error = FT_Load_Char(face1,index,FT_LOAD_DEFAULT);
	//printf("error%d\n",error);
        error = FT_Render_Glyph(glyf1,FT_RENDER_MODE_NORMAL);
	//printf("error%d\n",error);
        error = FT_Load_Char(face2,index,FT_LOAD_DEFAULT);
	//printf("error%d\n",error);
        error = FT_Render_Glyph(glyf2,FT_RENDER_MODE_NORMAL);
	//printf("error%d\n",error);
	for(int k=0;k<glyf1->bitmap.rows*glyf1->bitmap.width;k++){
	    if(glyf1->bitmap.buffer[k] != glyf2->bitmap.buffer[k]){
		num_of_not_same += 1;
		//printf("%ld,%d not working.\n",character,index);
		//for(int l=0;l<glyf1->bitmap.rows*glyf1->bitmap.width;l++)
		//    printf("%d,%d\n",glyf1->bitmap.buffer[l],glyf2->bitmap.buffer[l]);
	
		break;
	    }
	}
	character = FT_Get_Next_Char(face1,character,&index);
	if(!index)
	    break;

    }

    printf("**************** test done! %d/%d pass\n",itr-num_of_not_same,itr);





}

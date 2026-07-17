/*
** Assignment name : flood_fill
**
** Expected files  : flood_fill.c, flood_fill.h
** Allowed functions: None
**
** -----------------------------------------------------------------------
**
** Write a function that fills a zone by replacing characters with 'F'.
**
** The function receives a 2D array of chars, its size as a t_point,
** and a starting point. Starting from begin, it replaces all connected
** characters (same char as begin, connected horizontally or vertically)
** with 'F'. Diagonal connections do NOT count.
**
** Function prototype:
**   void flood_fill(char **tab, t_point size, t_point begin);
**
** Header file flood_fill.h must contain:
**
**   typedef struct s_point
**   {
**     int x;
**     int y;
**   } t_point;
**
** Example:
**   char *area[] = {
**     "11111",
**     "10001",
**     "10101",
**     "10001",
**     "11111",
**   };
**   flood_fill(area, {5, 5}, {0, 0});
**   // => all border '1's become 'F', inner zone untouched
*/

#ifndef FLOOD_FILL_H
# define FLOOD_FILL_H

typedef struct s_point
{
	int	x;
	int	y;
}	t_point;

#endif

void fill_helper(char **tab, t_point size, int y, int x, char target)
{
    if (y < 0 || y >= size.y || x < 0 || x >= size.x)
        return;
    if (tab[y][x] != target)
        return;
    tab[y][x] = 'F';
    fill_helper(tab, size, y, x + 1, target);
    fill_helper(tab, size, y, x - 1, target);
    fill_helper(tab, size, y + 1, x, target);
    fill_helper(tab, size, y - 1, x, target);
}

void	flood_fill(char **tab, t_point size, t_point begin)
{
	fill_helper(tab, size, begin.y, begin.x, tab[begin.y][begin.x]);
}

#include <stdio.h>

int	main(void)
{
	char	row0[] = "11111";
	char	row1[] = "10001";
	char	row2[] = "10101";
	char	row3[] = "10001";
	char	row4[] = "11111";
	char	*area[] = {row0, row1, row2, row3, row4};
	t_point	size = {5, 5};
	t_point	begin = {0, 0};

	flood_fill(area, size, begin);
	for (int i = 0; i < 5; i++)
		printf("%s\n", area[i]);
	printf("\n");

	char	r0[] = "11111";
	char	r1[] = "10001";
	char	r2[] = "10101";
	char	r3[] = "10001";
	char	r4[] = "11111";
	char	*area2[] = {r0, r1, r2, r3, r4};
	t_point	begin2 = {2, 2};

	flood_fill(area2, size, begin2);
	for (int i = 0; i < 5; i++)
		printf("%s\n", area2[i]);
	return (0);
}

/*
** Exercise: print_bits
**
** Prototype: void print_bits(unsigned char octet);
** Allowed functions: write
**
** Description:
**   Write a function that takes a byte and prints it in binary (MSB first),
**   without a newline at the end.
**
** Examples:
**   print_bits(2)   -> 00000010
**   print_bits(255) -> 11111111
**   print_bits(0)   -> 00000000
*/

#include <unistd.h>

void	print_bits(unsigned char octet)
{
	int		i;   // bit position, starts at 7 (MSB) and goes down to 0 (LSB)
	char	bit; // the character '0' or '1' we will write

	i = 7; // start from the most significant bit (leftmost)
	while (i >= 0) // loop through all 8 bit positions
	{
		// octet >> i  : shift octet right by i positions, putting bit i at position 0
		// & 1         : mask all bits except position 0, result is 0 or 1
		// + '0'       : convert integer 0/1 to ASCII character '0'/'1'
		bit = ((octet >> i) & 1) + '0';
		write(1, &bit, 1); // print the single character '0' or '1'
		i--; // move to the next bit position (toward LSB)
	}
}

int	main(void)
{
	print_bits(2);
	write(1, "\n", 1);
	print_bits(255);
	write(1, "\n", 1);
	print_bits(0);
	write(1, "\n", 1);
}

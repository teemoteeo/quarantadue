#include <stddef.h>  // for size_t/NULL

// Define the struct at the top of the file as 'typedef struct s_list { void *content; struct s_list *next; } t_list;'
// Define the size_t type for use with 'size_t' and NULL

typedef struct s_list {
  void *content;
  struct s_list *next;
} t_list;

// Prototype for the function
int ft_lstsize(t_list *lst);

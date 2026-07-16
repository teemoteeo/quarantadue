#include <stddef.h>  // for size_t, NULL

// Define the structure of a list node
typedef struct s_list {
    void *content;  // Pointer to the content of the list node
    struct s_list *next;  // Pointer to the next list node in the list

} t_list;

// Define the function prototype for the list iterator
void ft_lstiter(t_list *lst, void (*f)(void *));
```

This file contains the implementation of the `ft_lstiter` function, which iterates over the list using a provided function pointer.

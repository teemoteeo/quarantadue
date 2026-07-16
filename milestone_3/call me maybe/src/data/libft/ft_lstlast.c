#include <stddef.h>  // for size_t, NULL

// Define the structure of a list node
typedef struct s_list {
    void *content;
    struct s_list *next;  // Pointer to the next list node
} t_list;

// Define the function prototype for the list last element
t_list *ft_lstlast(t_list *lst);

// Implement the function ft_lstlast to return the last node of the list, or NULL if empty
t_list *ft_lstlast(t_list *lst) {
    // Check if the list is empty
    if (lst == NULL || lst->next == NULL) {
        // If the list is empty, return NULL
        return NULL;
    }

    // Return the last node of the list
    return lst->next;
}

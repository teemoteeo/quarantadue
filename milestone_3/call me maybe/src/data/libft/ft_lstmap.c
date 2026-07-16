#include <stddef.h>  // for size_t/NULL, malloc, free

// Define the struct t_list with a void *content and a pointer to the next node
typedef struct s_list {
    void *content;
    struct s_list *next;
} t_list;

// Define the function ft_lstmap with a void *(*f)(void *) and void (*del)(void *)
// Return a new list built by applying f to the content of every node; on allocation failure, clear the new list with del and return NULL
// There is no libft.h: define the struct at the top of the file as 'typedef struct s_list { void *content; struct s_list *next; } t_list;'
// Allowed libc: malloc, free
void *ft_lstmap(t_list *lst, void *(*f)(void *)) void (*del)(void *)) {
    t_list *new_lst = NULL;  // Initialize new list
    void *content = NULL;   // Initialize content of the list

    for (t_list *lst = lst; lst != NULL; lst = lst->next) {
        content = f(lst->content);  // Apply the function to the list's content
        if (f == NULL) {
            del(new_lst);  // Clear the list with malloc and return NULL
        }
    }

    return new_lst;  // Return the new list
}

// Define the function to allocate memory for a list and initialize its contents
void *malloc_list(void) {
    t_list *new_lst = NULL;  // Initialize new list
    void *content = NULL;   // Initialize content of the list

    for (t_list *lst = lst; lst != NULL; lst = lst->next) {
        content = f(lst->content);  // Apply the function to the list's content
        if (f == NULL) {
            return malloc(sizeof(t_list));  // Allocate memory for the list and initialize its contents
        }
    }

    return NULL;  // Return NULL if malloc fails
}

// Define the function to free memory allocated for a list
void free_list(void *lst) {
    t_list *new_lst = lst;  // Initialize the list
    while (new_lst != NULL) {
        del(new_lst);  // Clear the list with malloc and return
        new_lst = new_lst->next;  // Move to the next node in the list
    }
}

//

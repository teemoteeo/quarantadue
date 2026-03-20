/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   ft_lst_clear.c                                     :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: tcostant <tcostant@student.42.fr>          +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/11/26 16:19:00 by tcostant          #+#    #+#             */
/*   Updated: 2025/11/27 12:56:31 by tcostant         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "libft.h"

void	ft_lstdelone(t_list *lst, void (*del)(void *))
{
	del(lst->content);
	free(lst);
}

void	ft_lstclear(t_list **lst, void (*del)(void *))
{
	t_list	*tmp;

	while (*lst)
	{
		tmp = (*lst)->next;
		del((*lst)->content);
		free(*lst);
		*lst = tmp;
	}
	*lst = NULL;
}

// void	del(void *content)
// {
// 	free(content);
// }

// #include <stdio.h>

// int	main(void)
// {
// 	char	*content1 = ft_strdup("swag");
// 	char	*content2 = "swaaaaag";
// 	char	*content3 = "swaaaaaaaaag";

// 	t_list	*lst = ft_lstnew(content2);
// 	ft_lstadd_front(&lst, ft_lstnew(content1));
// 	ft_lstadd_back(&lst, ft_lstnew(content3));
// 	printf("dimensione lista: %d\n", ft_lstsize(lst));
// 	t_list *tmp = lst->next;
// 	ft_lstdelone(lst, del);
// 	lst = tmp;
// 	while (lst)
// 	{
// 		printf("%s\n", (char *)lst->content);
// 		lst = lst->next;
// 	}
// 	ft_lstclear(&lst, del);
// 	if(lst == NULL)
// 		printf("List cleared succesfully.\n");
// }

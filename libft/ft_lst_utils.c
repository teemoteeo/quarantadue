/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   ft_lst_utils.c                                     :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: tcostant <tcostant@student.42.fr>          +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/11/26 15:07:57 by tcostant          #+#    #+#             */
/*   Updated: 2025/11/26 18:43:01 by tcostant         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "libft.h"

int	ft_lstsize(t_list *lst)
{
	int	i;

	i = 0;
	while (lst)
	{
		lst = lst->next;
		i++;
	}
	return (i);
}

t_list	*ft_lstlast(t_list *lst)
{
	while (lst)
	{
		if (lst->next == NULL)
			return (lst);
		lst = lst->next;
	}
	return (NULL);
}

void	ft_lstadd_back(t_list **lst, t_list *new)
{
	t_list	*last;

	if (*lst == NULL)
		*lst = new;
	else
	{
		last = ft_lstlast(*lst);
		last->next = new;
		new->next = NULL;
	}
}

// #include <stdio.h>

// int	main(void)
// {
// 	char	*content1 = "swag";
// 	char	*content2 = "swaaaaag";
// 	char	*content3 = "swaaaaaaaaag";

// 	t_list	*lst = ft_lstnew(content2);
// 	ft_lstadd_front(&lst, ft_lstnew(content1));
// 	ft_lstadd_back(&lst, ft_lstnew(content3));
// 	printf("dimensione lista: %d\n", ft_lstsize(lst));
// 	while (lst)
// 	{
// 		printf("%s\n", (char *)lst->content);
// 		lst = lst->next;
// 	}
// }
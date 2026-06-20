/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   coder.c                                            :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: teemoteeo <teemoteeo@student.42.fr>        +#+  +:+       +#+    */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/06/04 00:00:00 by teemoteeo        #+#   #+#             */
/*   Updated: 2026/06/19 00:00:00 by teemoteeo        ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "codexion.h"

void	*coder_routine(void *arg)
{
	t_coder		*c;
	t_dongle	*left;
	t_dongle	*right;

	c = (t_coder *)arg;
	left = &c->sim->dongles[c->left_dongle];
	right = &c->sim->dongles[c->right_dongle];
	c->last_compile_start = now_ms();
	while (c->compiles_done < c->sim->compiles_required)
	{
		c->state = CODER_WAITING_DONGLE;
		c->wait_since = now_ms();
		if (acquire_both_dongles(c, left, right) != 0)
			return (NULL);
		coder_do_compile(c, left, right);
		if (check_stop(c->sim))
			return (NULL);
		coder_do_debug(c);
		if (check_stop(c->sim))
			return (NULL);
		coder_do_refactor(c);
		if (check_stop(c->sim))
			return (NULL);
	}
	c->state = CODER_DONE;
	return (NULL);
}

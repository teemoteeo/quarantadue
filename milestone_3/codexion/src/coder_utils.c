/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   coder_utils.c                                      :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: teemoteeo <teemoteeo@student.42.fr>        +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/06/04 00:00:00 by teemoteeo        #+#    #+#              */
/*   Updated: 2026/06/04 00:00:00 by teemoteeo       ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "codexion.h"

int	check_stop(t_simulation *sim)
{
	int	stop;

	pthread_mutex_lock(&sim->stop_mutex);
	stop = sim->stop_flag;
	pthread_mutex_unlock(&sim->stop_mutex);
	return (stop);
}

static void	coder_do_compile(t_coder *c, t_dongle *left, t_dongle *right)
{
	c->last_compile_start = now_ms();
	c->state = CODER_COMPILING;
	log_msg(c->sim, c->id, "is compiling");
	ft_usleep(c->sim->time_to_compile);
	dongle_release(left);
	dongle_release(right);
	c->compiles_done++;
}

static int	coder_do_debug(t_coder *c)
{
	c->state = CODER_DEBUGGING;
	log_msg(c->sim, c->id, "is debugging");
	ft_usleep(c->sim->time_to_debug);
	return (check_stop(c->sim));
}

static int	coder_do_refactor(t_coder *c)
{
	c->state = CODER_REFACTORING;
	log_msg(c->sim, c->id, "is refactoring");
	ft_usleep(c->sim->time_to_refactor);
	return (check_stop(c->sim));
}

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
		if (acquire_both_dongles(c, left, right) != 0)
			return (NULL);
		coder_do_compile(c, left, right);
		if (check_stop(c->sim))
			return (NULL);
		if (coder_do_debug(c))
			return (NULL);
		if (coder_do_refactor(c))
			return (NULL);
	}
	c->state = CODER_DONE;
	return (NULL);
}

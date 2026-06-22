/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   coder_utils.c                                      :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: teemoteeo <teemoteeo@student.42.fr>        +#+  +:+       +#+    */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/06/04 00:00:00 by teemoteeo        #+#   #+#             */
/*   Updated: 2026/06/19 00:00:00 by teemoteeo        ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "codexion.h"

/*
 * Single coder: only one dongle exists, so two can never be held at once.
 * The coder keeps its lone dongle and waits until the monitor flags burnout.
 */
static int	wait_single_dongle(t_coder *c, t_dongle *dongle1)
{
	while (!check_stop(c->sim))
		ft_usleep(1);
	dongle_release(dongle1);
	return (-1);
}

int	acquire_both_dongles(t_coder *c, t_dongle *left, t_dongle *right)
{
	t_dongle	*dongle1;
	t_dongle	*dongle2;

	if (c->left_dongle <= c->right_dongle)
	{
		dongle1 = left;
		dongle2 = right;
	}
	else
	{
		dongle1 = right;
		dongle2 = left;
	}
	if (scheduler_request_single(c->sim, c->id, dongle1) != 0)
		return (-1);
	log_state(c->sim, c->id, "has taken a dongle");
	if (check_stop(c->sim))
	{
		dongle_release(dongle1);
		return (-1);
	}
	if (dongle1 == dongle2)
		return (wait_single_dongle(c, dongle1));
	while (!dongle_try_acquire(dongle2))
	{
		if (check_stop(c->sim))
		{
			dongle_release(dongle1);
			return (-1);
		}
		ft_usleep(1);
	}
	if (check_stop(c->sim))
	{
		dongle_release(dongle1);
		dongle_release(dongle2);
		return (-1);
	}
	log_state(c->sim, c->id, "has taken a dongle");
	return (0);
}

int	check_stop(t_simulation *sim)
{
	int	stopped;

	pthread_mutex_lock(&sim->stop_mutex);
	stopped = sim->stop_flag;
	pthread_mutex_unlock(&sim->stop_mutex);
	return (stopped);
}

void	set_stop(t_simulation *sim)
{
	pthread_mutex_lock(&sim->stop_mutex);
	sim->stop_flag = 1;
	pthread_mutex_unlock(&sim->stop_mutex);
}

void	coder_do_compile(t_coder *c, t_dongle *left, t_dongle *right)
{
	set_last_compile(c, now_ms());
	log_state(c->sim, c->id, "is compiling");
	ft_usleep(c->sim->time_to_compile);
	dongle_release(left);
	dongle_release(right);
	c->compiles_done++;
}

void	coder_do_debug(t_coder *c)
{
	log_state(c->sim, c->id, "is debugging");
	ft_usleep(c->sim->time_to_debug);
}

void	coder_do_refactor(t_coder *c)
{
	log_state(c->sim, c->id, "is refactoring");
	ft_usleep(c->sim->time_to_refactor);
}

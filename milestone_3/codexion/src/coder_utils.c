/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   coder_utils.c                                      :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: teemoteeo <teemoteeo@student.42.fr>        +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/06/04 00:00:00 by teemoteeo        #+#    #+#             */
/*   Updated: 2026/06/19 00:00:00 by teemoteeo       ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "codexion.h"

/*
 * Coder singolo: esiste un solo dongle, quindi non se ne possono tenere due
 * contemporaneamente. Il coder tiene il suo unico dongle e aspetta che il
 * monitor segnali il burnout.
 */
static int	wait_single_dongle(t_coder *c, t_dongle *dongle1)
{
	while (!check_stop(c->sim))
		ft_usleep(1);
	dongle_release(dongle1);
	return (-1);
}

/* Secondo dongle: nessuno scheduler, il deadlock è già escluso dall'ordine. */
static int	acquire_second_dongle(t_coder *c, t_dongle *d1, t_dongle *d2)
{
	while (!dongle_try_acquire(d2))
	{
		if (check_stop(c->sim))
		{
			dongle_release(d1);
			return (-1);
		}
		ft_usleep(1);
	}
	if (check_stop(c->sim))
	{
		dongle_release(d1);
		dongle_release(d2);
		return (-1);
	}
	log_state(c->sim, c->id, "has taken a dongle");
	return (0);
}

int	acquire_both_dongles(t_coder *c, t_dongle *left, t_dongle *right)
{
	t_dongle	*first;
	t_dongle	*second;

	first = left;
	second = right;
	/* Ordine per indice: previene il deadlock (resource ordering classico). */
	if (c->left_dongle > c->right_dongle)
	{
		first = right;
		second = left;
	}
	if (scheduler_request_single(c->sim, c->id, first) != 0)
		return (-1);
	log_state(c->sim, c->id, "has taken a dongle");
	if (check_stop(c->sim))
	{
		dongle_release(first);
		return (-1);
	}
	if (first == second)
		return (wait_single_dongle(c, first));
	return (acquire_second_dongle(c, first, second));
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

/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   coder.c                                            :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: teemoteeo <teemoteeo@student.42.fr>        +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/06/04 00:00:00 by teemoteeo        #+#    #+#             */
/*   Updated: 2026/06/04 00:00:00 by teemoteeo       ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "codexion.h"

static int	try_acquire(t_dongle *d, t_coder *c)
{
	pthread_mutex_lock(&d->mutex);
	if (d->state == DONGLE_COOLDOWN && now_ms() >= d->cooldown_until)
		d->state = DONGLE_FREE;
	if (d->state != DONGLE_FREE)
	{
		pthread_mutex_unlock(&d->mutex);
		return (0);
	}
	d->state = DONGLE_HELD;
	d->held_by = c->id;
	pthread_mutex_unlock(&d->mutex);
	return (1);
}

static int	acquire_loop(t_coder *c, t_dongle *first, t_dongle *second)
{
	if (check_stop(c->sim))
		return (-1);
	if (!try_acquire(first, c))
	{
		ft_usleep(1);
		return (2);
	}
	log_msg(c->sim, c->id, "has taken a dongle");
	if (first == second)
		return (0);
	if (!try_acquire(second, c))
	{
		dongle_release(first);
		ft_usleep(1);
		return (2);
	}
	log_msg(c->sim, c->id, "has taken a dongle");
	return (0);
}

/* Acquire both dongles in index order to avoid deadlock. */
int	acquire_both_dongles(t_coder *c, t_dongle *left, t_dongle *right)
{
	t_dongle	*first;
	t_dongle	*second;
	int			rc;

	if (c->left_dongle <= c->right_dongle)
	{
		first = left;
		second = right;
	}
	else
	{
		first = right;
		second = left;
	}
	while (1)
	{
		rc = acquire_loop(c, first, second);
		if (rc != 2)
			return (rc);
	}
}

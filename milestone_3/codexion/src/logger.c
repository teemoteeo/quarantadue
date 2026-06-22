/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   logger.c                                           :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: teemoteeo <teemoteeo@student.42.fr>        +#+  +:+       +#+    */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/06/04 00:00:00 by teemoteeo        #+#   #+#             */
/*   Updated: 2026/06/19 00:00:00 by teemoteeo        ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "codexion.h"
#include <unistd.h>

/* Append a non-negative integer to buf; returns digits written. */
static int	put_ll(char *buf, long long n)
{
	char	tmp[24];
	int		i;
	int		len;

	i = 0;
	if (n <= 0)
		tmp[i++] = '0';
	while (n > 0)
	{
		tmp[i++] = (char)('0' + n % 10);
		n /= 10;
	}
	len = 0;
	while (i > 0)
		buf[len++] = tmp[--i];
	return (len);
}

long long	timestamp_ms(const t_simulation *sim)
{
	struct timeval	tv;
	long long		now;

	gettimeofday(&tv, NULL);
	now = (long long)tv.tv_sec * 1000 + tv.tv_usec / 1000;
	return (now - sim->start_time);
}

static void	print_locked(t_simulation *sim, int coder_id, const char *msg)
{
	char	buf[256];
	int		len;
	int		i;

	len = put_ll(buf, timestamp_ms(sim));
	buf[len++] = ' ';
	len += put_ll(buf + len, coder_id);
	buf[len++] = ' ';
	i = 0;
	while (msg[i])
		buf[len++] = msg[i++];
	buf[len++] = '\n';
	write(STDOUT_FILENO, buf, len);
}

/* Forced log (monitor / burnout): always printed. */
void	log_msg(t_simulation *sim, int coder_id, const char *msg)
{
	pthread_mutex_lock(&sim->log_mutex);
	print_locked(sim, coder_id, msg);
	pthread_mutex_unlock(&sim->log_mutex);
}

/*
 * Coder state log: dropped if the simulation has already stopped, so no
 * state line can appear after the terminal "burned out" message.
 */
void	log_state(t_simulation *sim, int coder_id, const char *msg)
{
	pthread_mutex_lock(&sim->log_mutex);
	if (check_stop(sim))
	{
		pthread_mutex_unlock(&sim->log_mutex);
		return ;
	}
	print_locked(sim, coder_id, msg);
	pthread_mutex_unlock(&sim->log_mutex);
}

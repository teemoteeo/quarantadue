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
#include <stdio.h>
#include <unistd.h>

long long	timestamp_ms(const t_simulation *sim)
{
	struct timeval	tv;
	long long		now;

	gettimeofday(&tv, NULL);
	now = (long long)tv.tv_sec * 1000 + tv.tv_usec / 1000;
	return (now - sim->start_time);
}

void	log_msg(t_simulation *sim, int coder_id, const char *msg)
{
	char	buf[256];
	int		len;

	pthread_mutex_lock(&sim->log_mutex);
	len = snprintf(buf, sizeof(buf), "%lld %d %s\n",
			timestamp_ms(sim), coder_id, msg);
	write(STDOUT_FILENO, buf, len);
	pthread_mutex_unlock(&sim->log_mutex);
}

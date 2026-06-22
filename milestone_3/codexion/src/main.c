/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   main.c                                             :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: teemoteeo <teemoteeo@student.42.fr>        +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/06/04 00:00:00 by teemoteeo        #+#    #+#              */
/*   Updated: 2026/06/04 00:00:00 by teemoteeo       ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "codexion.h"
#include <stdlib.h>
#include <stdio.h>

int	main(int argc, char **argv)
{
	t_simulation	sim;

	if (parse_args(argc, argv, &sim) != 0)
	{
		fprintf(stderr, "Usage: %s <nb_coders> <time_to_burnout> "
			"<time_to_compile> <time_to_debug> <time_to_refactor> "
			"<compiles_required> <dongle_cooldown> <scheduler>\n",
			argv[0]);
		return (EXIT_FAILURE);
	}
	simulation_init(&sim);
	simulation_run(&sim);
	simulation_cleanup(&sim);
	return (EXIT_SUCCESS);
}

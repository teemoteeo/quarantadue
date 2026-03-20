def ft_count_harvest_iterative():
    days_to_harvest = int(input("Days until harvest: "))
    days_passed = 0
    while days_passed < days_to_harvest:
        days_passed += 1
        print(f"Day {days_passed}")
    print("Harvest time!")

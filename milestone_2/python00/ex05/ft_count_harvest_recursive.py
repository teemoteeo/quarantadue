def ft_count_harvest_recursive():
    days_to_harvest = int(input("Days until harvest: "))
    days_passed = 0

    def count_days(days_passed):
        if days_passed < days_to_harvest:
            days_passed += 1
            print(f"Day {days_passed}")
            count_days(days_passed)
        else:
            print("Harvest time!")

    count_days(days_passed)

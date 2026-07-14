def main():
    while True:
        user_input = input("문장을 입력하세요: ")
        if user_input == "!quit":
            break
        print("입력하신 문장은:", user_input)


if __name__ == "__main__":
    main()
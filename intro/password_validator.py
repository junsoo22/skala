import re

PASSWORD_PATTERN = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^a-zA-Z0-9]).+$"
)


def is_valid_password(password: str) -> bool:
    return bool(PASSWORD_PATTERN.match(password))


def main():
    while True:
        password = input("비밀번호를 입력하세요 (종료: !quit): ")
        if password == "!quit":
            break
        if is_valid_password(password):
            print("유효한 비밀번호입니다.")
        else:
            print("비밀번호는 영문 소문자, 대문자, 숫자, 기호를 각각 최소 하나 이상 포함해야 합니다.")


if __name__ == "__main__":
    main()

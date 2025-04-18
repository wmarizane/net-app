def extract_temp_message(input_str):
    parts = input_str.strip().split()

    if not parts or parts[0] != ".temp":
        return None  # or raise an error

    users = []
    message_start_index = None

    for i in range(1, len(parts)):
        if parts[i].startswith('@'):
            users.append(parts[i][1:])
        else:
            message_start_index = i
            break

    message = ' '.join(parts[message_start_index:]) if message_start_index is not None else ''

    return {
        'users': users,
        'message': message
    }


user_inpit = ".temp @user1 @user2 Hello world"

print(extract_temp_message(user_inpit))
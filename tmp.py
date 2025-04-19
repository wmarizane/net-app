def extract_reply_message(input_str):
    parts = input_str.strip().split()

    if not parts or parts[0] != ".reply":
        return None  # or raise an error

    if len(parts) < 3:
        return None  # Not enough parts for msg_id and msg_context

    msg_id = parts[1]
    msg_content = ' '.join(parts[2:])

    return msg_id, msg_content


msg_id, msg_content = extract_reply_message(".reply 1234678 Hello concac")

print(msg_id)
print(msg_content)
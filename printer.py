from datetime import datetime
import logging
USB_PATH = "/dev/usb/lp0"

# ESC/POS commands
CUT = b'\x1d\x56\x41\x00'
FEED = b'\n\n\n'

def generate_receipt(data):
    now = datetime.now()

    lines = []
    grade = data["grade"]
    lines.append("=" * 32)
    lines.append("   COPRA QUALITY ANALYSIS")
    lines.append("        SYSTEM RECEIPT")
    lines.append("=" * 32)

    lines.append(f"Date: {data.get('date') or now.strftime('%b %d, %Y')}")
    lines.append(f"Time: {data.get('time') or now.strftime('%I:%M %p')}")
    lines.append("-" * 32)

    lines.append(f"Operator: {data.get('operator', 'N/A')}")
    lines.append(f"Batch No: {data['batch']}")
    if isinstance(grade, int) and grade in (1, 2, 3):
        lines.append(f"Final Grade: GRADE {grade}")
    else:
        lines.append("Final Grade: REJECT")
    lines.append("-" * 32)

    lines.append("Batch Breakdown:")
    lines.append(f"G1: {data['g1']}")
    lines.append(f"G2: {data['g2']}")
    lines.append(f"G3: {data['g3']}")
    lines.append(f"Reject: {data['reject']}")
    lines.append("-" * 32)
    total = data['g1'] + data['g2'] + data['g3'] + data['reject']
    lines.append(f"Total Copra: {total}")
    lines.append("-" * 32)
    
    lines.append(f"Recommendation:")
    lines.append(data.get("recommendation", "N/A"))
    lines.append("-" * 32)

    lines.append("   Thank you!")
    lines.append("=" * 32)

    return "\n".join(lines) + "\n"


def print_to_terminal(receipt_text):
    print(receipt_text)


def print_to_usb(receipt_text):
    try:
        with open(USB_PATH, "wb") as printer:
            printer.write(receipt_text.encode("utf-8"))
            printer.write(FEED)
            printer.write(CUT)
        print("[+] Printed successfully via USB")
    except Exception as e:
        logging.error(f"Something went wrong: {e}", exc_info=True)


def save_receipt(receipt_text, filename="receipt.txt"):
    with open(filename, "w") as f:
        f.write(receipt_text)
    print(f"[+] Receipt saved to {filename}")


if __name__ == "__main__":
    receipt = generate_receipt()

    # 1. Show in terminal
    print_to_terminal(receipt)

    # 2. Print to thermal printer
    print_to_usb(receipt)

    # 3. Save to file (optional)
    save_receipt(receipt)
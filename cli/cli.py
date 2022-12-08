"""
Command line interface for Artie. Connects to USB in controller module.
"""
import argparse
import serial

#####################################################################################
########### Parsing Functions : Add to Jumptable when you add one ###################
#####################################################################################

def print_help():
    """
    Prints all the help messages.
    """
    print("Available commands:")
    for cmd, cmdfn in CMD_JUMPTABLE.items():
        print(f"{cmd}: {cmdfn.__doc__}")

def parse_led(cmd: str):
    """
    Controls the specified LED.
            ----------------------
            led <NODE> <ON/OFF>
            ----------------------

            ARGS
            ----
            NODE => must be a node identifier. Currently only 0 is allowed.
            off  => Turn off the specified LED.
            on   => Turn on the specified LED.
    """
    cmd_items = cmd.split()
    if len(cmd_items) != len("led NODE ON_OFF".split()):
        return None, "Incorrect number of args. Require <NODE> and <ON/OFF>"

    node_id = cmd_items[1]
    if node_id != "0":
        return None, "Invalid node ID. Currently only 0 is allowed."

    on_or_off = cmd_items[2]
    if on_or_off == "on":
        on_or_off = "1"
    elif on_or_off == "off":
        on_or_off = "0"
    else:
        return None, "Invalid LED state. Valid ones are 'on' or 'off'"

    return f"A {node_id} {on_or_off}"

def parse_test(cmd: str):
    """
    Runs the test suite, printing the results to console.
            ----------------------
            test <ON/OFF>
            ----------------------

            ARGS
            ----
            off => Turn off LED connected to CAN Bus rx circuit
            on  => Turn on LED connected to CAN Bus rx circuit
    """
    cmd_items = cmd.split()
    if len(cmd_items) != len("test ON_OFF".split()):
        return None, "Incorrect number of args. Require <ON/OFF>"

    on_or_off = cmd_items[1]
    if on_or_off == "on":
        on_or_off = "1"
    elif on_or_off == "off":
        on_or_off = "0"
    else:
        return None, "Invalid LED state. Valid ones are 'on' or 'off'"

    return f"B {on_or_off}"

# Each of these functions should return a tuple of (CMD for serial, error message)
# Each command should also be documented with a help string - as these strings are
# parsed and printed for the help message.
CMD_JUMPTABLE = {
    "led": parse_led,
    "test": parse_test,
}
#####################################################################################
#####################################################################################
#####################################################################################

def parse_command(cmd: str):
    """
    Parses the given command and returns a tuple of (CMD for serial, error message).
    """
    cmd = cmd.lower().strip()

    if cmd == "help":
        return "help", None
    elif cmd in CMD_JUMPTABLE:
        return CMD_JUMPTABLE[cmd]
    else:
        return None, "Invalid command. Try 'help'"

if __name__ == "__main__":
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("port", type=str, help="Port or COM number.")
    args = parser.parse_args()

    # Connect to command module
    baudrate = 9600
    ser = serial.Serial(args.port, baudrate)
    ser.open()

    # Loop: interpreting user's inputs and outputing commands
    while True:
        cmd = input("CMD:")
        parsed_cmd, err = parse_command(cmd)
        if parsed_cmd == "help":
            print_help()
        elif err is None:
            ser.write((parsed_cmd.rstrip() + "\n").encode('utf-8'))
            out = ser.read_until('\n').decode()
            print(out)
        else:
            print("Invalid command:", err)
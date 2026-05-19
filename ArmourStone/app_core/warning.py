### Warning function, taken from Tutorial 9 of the KBE Course

def warn(warning_header, msg):
    """Generate a warning dialog box, wait for user confirmation and close it.

    Parameters
    ----------
    warning_header : str
        String shown in the window header.
    msg : str
        String shown in the body of the message window

    Returns
    -------
    None.

    """
    # tkinter is a built-in GUI library in Python
    from tkinter import Tk, messagebox

    # initialization
    window = Tk()
    window.withdraw()

    # generates message box and waits for user to close it
    messagebox.showwarning(warning_header, msg)

    # close the message window, terminate the associated process
    window.deiconify()
    window.destroy()
    window.quit()
from parapy import core as ppc
import re
from input import project_name, project_nr
from app_core.warning import warn

class Project(ppc.Base):

    input_project_name = ppc.Input(project_name, doc="Project name used for file and folder naming. Spaces are converted to underscores.")
    input_project_nr = ppc.Input(project_nr, doc="Project number used for file and folder naming. Spaces are converted to underscores.")

    @ppc.Attribute
    def project_name(self):
        """
        Fix project name and check validity.

        :return: Project name.
        """
        raw = self.input_project_name
        name = str(raw).strip()
        name = name.replace(" ", "_")
        # Remove special characters that would be invalid for a file/folder name
        name = re.sub(r"[^A-Za-z0-9_.-]", "", name)
        if not name:
            warn("Invalid project name", f"Name cannot be empty or only contain invalid characters. Please enter a valid name.")
            raise ValueError(f"Name cannot be empty or only contain invalid characters.")
        return name
    
    @ppc.Attribute
    def project_nr(self):
        """
        Check validity of project number.

        :return: Project number.
        """
        if not isinstance(self.input_project_nr, int):
            warn("Invalid project number", "Project number must be an integer. Please enter a valid project number.")
            raise ValueError("Project number must be an integer.")

        return str(self.input_project_nr)
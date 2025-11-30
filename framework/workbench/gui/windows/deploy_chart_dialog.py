"""
This module contains the code for the 'deploy Helm Chart' dialog.
"""
from PyQt6 import QtWidgets, QtCore
from comms import tool
from model import artie_profile
from model import settings
import subprocess
import threading


class DeployChartDialog(QtWidgets.QDialog):
    """Dialog for deploying Helm charts to Artie"""
    
    def __init__(self, workbench_settings: settings.WorkbenchSettings, current_profile: artie_profile.ArtieProfile, parent=None):
        super().__init__(parent)
        self.current_profile = current_profile
        self.settings = workbench_settings
        self.deployment_thread = None
        
        self.setWindowTitle("Deploy Helm Chart")
        self.setModal(True)
        self.setMinimumSize(600, 500)
        
        self._setup_ui()
        self._load_available_charts()
    
    def _setup_ui(self):
        """Setup the dialog UI"""
        layout = QtWidgets.QVBoxLayout(self)
        
        # Chart selection section
        chart_group = QtWidgets.QGroupBox("Chart Selection")
        chart_layout = QtWidgets.QVBoxLayout(chart_group)
        
        self.chart_list = QtWidgets.QListWidget()
        self.chart_list.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        chart_layout.addWidget(self.chart_list)
        
        # Chart description
        desc_label = QtWidgets.QLabel("Description:")
        chart_layout.addWidget(desc_label)
        
        self.chart_description = QtWidgets.QTextBrowser()
        self.chart_description.setMaximumHeight(80)
        chart_layout.addWidget(self.chart_description)
        
        layout.addWidget(chart_group)
        
        # Options section
        options_group = QtWidgets.QGroupBox("Deployment Options")
        options_layout = QtWidgets.QFormLayout(options_group)
        
        # Artie name
        self.artie_name_input = QtWidgets.QLineEdit()
        self.artie_name_input.setText(self.current_profile.name if self.current_profile else "")
        options_layout.addRow("Artie Name:", self.artie_name_input)
        
        # Docker options
        self.docker_repo_input = QtWidgets.QLineEdit()
        self.docker_repo_input.setPlaceholderText("Optional - Docker repository")
        options_layout.addRow("Docker Repo:", self.docker_repo_input)
        
        self.docker_tag_input = QtWidgets.QLineEdit()
        self.docker_tag_input.setPlaceholderText("Optional - uses git hash if empty")
        options_layout.addRow("Docker Tag:", self.docker_tag_input)
        
        self.docker_username_input = QtWidgets.QLineEdit()
        self.docker_username_input.setPlaceholderText("Optional - for private repos")
        options_layout.addRow("Docker Username:", self.docker_username_input)
        
        self.docker_password_input = QtWidgets.QLineEdit()
        self.docker_password_input.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        self.docker_password_input.setPlaceholderText("Optional - for private repos")
        options_layout.addRow("Docker Password:", self.docker_password_input)
        
        # Advanced options
        advanced_layout = QtWidgets.QHBoxLayout()
        
        self.force_build_checkbox = QtWidgets.QCheckBox("Force Rebuild")
        self.force_build_checkbox.setToolTip("Force rebuild even if artifacts exist")
        advanced_layout.addWidget(self.force_build_checkbox)
        
        self.docker_no_cache_checkbox = QtWidgets.QCheckBox("No Docker Cache")
        self.docker_no_cache_checkbox.setToolTip("Pass --no-cache to Docker builds")
        advanced_layout.addWidget(self.docker_no_cache_checkbox)
        
        self.docker_logs_checkbox = QtWidgets.QCheckBox("Show Docker Logs")
        self.docker_logs_checkbox.setToolTip("Print Docker logs during build")
        advanced_layout.addWidget(self.docker_logs_checkbox)
        
        advanced_layout.addStretch()
        options_layout.addRow(advanced_layout)
        
        layout.addWidget(options_group)
        
        # Output section
        output_group = QtWidgets.QGroupBox("Deployment Output")
        output_layout = QtWidgets.QVBoxLayout(output_group)
        
        self.output_text = QtWidgets.QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setPlaceholderText("Deployment output will appear here...")
        output_layout.addWidget(self.output_text)
        
        layout.addWidget(output_group)
        
        # Progress bar
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)
        
        # Button box
        button_box = QtWidgets.QDialogButtonBox()
        
        self.deploy_button = QtWidgets.QPushButton("Deploy")
        self.deploy_button.setEnabled(False)
        self.deploy_button.clicked.connect(self._deploy)
        button_box.addButton(self.deploy_button, QtWidgets.QDialogButtonBox.ButtonRole.ActionRole)
        
        self.cancel_button = QtWidgets.QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_box.addButton(self.cancel_button, QtWidgets.QDialogButtonBox.ButtonRole.RejectRole)
        
        layout.addWidget(button_box)
        
        # Connect signals
        self.chart_list.currentItemChanged.connect(self._on_chart_selected)
    
    def _load_available_charts(self):
        """Load available Helm charts from artie-tool.py"""
        artie_tool = tool.ArtieToolInvoker(self.current_profile)
        err, deployment_names = artie_tool.list_deployments()
        if err:
            self.output_text.append(f"Error loading charts: {err}")
            return
        
        for deployment_name in deployment_names:
            item = QtWidgets.QListWidgetItem(deployment_name)
            item.setData(QtCore.Qt.ItemDataRole.UserRole, "TODO: Describe the different charts")  # TODO: Placeholder for description
            self.chart_list.addItem(item)

    def _on_chart_selected(self, current, previous):
        """Handle chart selection"""
        if current:
            self.deploy_button.setEnabled(True)
            description = current.data(QtCore.Qt.ItemDataRole.UserRole)
            self.chart_description.setText(description)
        else:
            self.deploy_button.setEnabled(False)
            self.chart_description.clear()
    
    def _build_command(self):
        """Build the deployment command"""
        selected_item = self.chart_list.currentItem()
        if not selected_item:
            return None
        
        chart_name = selected_item.text()
        
        cmd = ["python", "artie-tool.py", "deploy", chart_name]
        
        # Add artie name if provided
        artie_name = self.artie_name_input.text().strip()
        if artie_name:
            cmd.extend(["--artie-name", artie_name])
        
        # Add docker options
        docker_repo = self.docker_repo_input.text().strip()
        if docker_repo:
            cmd.extend(["--docker-repo", docker_repo])
        
        docker_tag = self.docker_tag_input.text().strip()
        if docker_tag:
            cmd.extend(["--docker-tag", docker_tag])
        
        docker_username = self.docker_username_input.text().strip()
        if docker_username:
            cmd.extend(["--docker-username", docker_username])
        
        docker_password = self.docker_password_input.text().strip()
        if docker_password:
            cmd.extend(["--docker-password", docker_password])
        
        # Add flags
        if self.force_build_checkbox.isChecked():
            cmd.append("--force-build")
        
        if self.docker_no_cache_checkbox.isChecked():
            cmd.append("--docker-no-cache")
        
        if self.docker_logs_checkbox.isChecked():
            cmd.append("--docker-logs")
        
        return cmd
    
    def _deploy(self):
        """Start the deployment process"""
        cmd = self._build_command()
        if not cmd:
            QtWidgets.QMessageBox.warning(
                self,
                "No Chart Selected",
                "Please select a chart to deploy."
            )
            return
        
        # Disable UI during deployment
        self.deploy_button.setEnabled(False)
        self.chart_list.setEnabled(False)
        self.progress_bar.show()
        self.output_text.clear()
        self.output_text.append(f"Running: {' '.join(cmd)}\n")
        
        # Run deployment in a separate thread
        self.deployment_thread = threading.Thread(target=self._run_deployment, args=(cmd,))
        self.deployment_thread.start()
    
    def _run_deployment(self, cmd):
        """Run the deployment command"""
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd="c:\\Users\\strangem\\repos\\Artie\\framework",
                bufsize=1,
                universal_newlines=True
            )
            
            # Read output line by line
            for line in process.stdout:
                # Use Qt signal to update UI from main thread
                QtCore.QMetaObject.invokeMethod(
                    self.output_text,
                    "append",
                    QtCore.Qt.ConnectionType.QueuedConnection,
                    QtCore.Q_ARG(str, line.rstrip())
                )
            
            process.wait()
            
            # Update UI when done
            if process.returncode == 0:
                QtCore.QMetaObject.invokeMethod(
                    self,
                    "_deployment_success",
                    QtCore.Qt.ConnectionType.QueuedConnection
                )
            else:
                QtCore.QMetaObject.invokeMethod(
                    self,
                    "_deployment_failed",
                    QtCore.Qt.ConnectionType.QueuedConnection,
                    QtCore.Q_ARG(int, process.returncode)
                )
        
        except Exception as e:
            QtCore.QMetaObject.invokeMethod(
                self,
                "_deployment_error",
                QtCore.Qt.ConnectionType.QueuedConnection,
                QtCore.Q_ARG(str, str(e))
            )
    
    @QtCore.pyqtSlot()
    def _deployment_success(self):
        """Handle successful deployment"""
        self.progress_bar.hide()
        self.output_text.append("\n✓ Deployment completed successfully!")
        self.deploy_button.setText("Deploy Again")
        self.deploy_button.setEnabled(True)
        self.chart_list.setEnabled(True)
        
        QtWidgets.QMessageBox.information(
            self,
            "Deployment Complete",
            "Helm chart deployed successfully!"
        )
    
    @QtCore.pyqtSlot(int)
    def _deployment_failed(self, return_code):
        """Handle failed deployment"""
        self.progress_bar.hide()
        self.output_text.append(f"\n✗ Deployment failed with return code: {return_code}")
        self.deploy_button.setEnabled(True)
        self.chart_list.setEnabled(True)
        
        QtWidgets.QMessageBox.warning(
            self,
            "Deployment Failed",
            f"Deployment failed with return code: {return_code}\nCheck output for details."
        )
    
    @QtCore.pyqtSlot(str)
    def _deployment_error(self, error_msg):
        """Handle deployment error"""
        self.progress_bar.hide()
        self.output_text.append(f"\n✗ Error: {error_msg}")
        self.deploy_button.setEnabled(True)
        self.chart_list.setEnabled(True)
        
        QtWidgets.QMessageBox.critical(
            self,
            "Deployment Error",
            f"An error occurred during deployment:\n{error_msg}"
        )

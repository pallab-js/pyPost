from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTextEdit, QGroupBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QProgressBar, QCheckBox,
    QScrollArea, QWidget as QWidget2, QFrame
)
from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtGui import QColor, QFont
from typing import List, Dict, Any
import json

from security.scanner import SecurityScanner, SecurityReport, Severity, get_risk_level


class SecurityScanWorker(QThread):
    finished = Signal(SecurityReport)
    progress = Signal(str)
    error = Signal(str)

    def __init__(self, scanner: SecurityScanner, url: str, method: str,
                 headers: Dict[str, str], body: Any = None):
        super().__init__()
        self.scanner = scanner
        self.url = url
        self.method = method
        self.headers = headers
        self.body = body

    def run(self):
        try:
            self.progress.emit("Scanning request...")
            request_report = self.scanner.scan_request(
                self.url, self.method, self.headers, self.body
            )
            self.progress.emit("Scanning response...")
            response_report = self.scanner.scan_response(
                self.url, self.method, 200, self.headers, self.body
            )
            combined_findings = request_report.findings + response_report.findings
            final_report = SecurityReport(
                url=self.url,
                method=self.method,
                findings=combined_findings,
                risk_score=max(request_report.risk_score, response_report.risk_score)
            )
            self.finished.emit(final_report)
        except Exception as e:
            self.error.emit(str(e))


class SecurityScannerDialog(QDialog):
    def __init__(self, parent=None, url: str = "", method: str = "GET",
                 headers: Dict[str, str] = None, body: Any = None):
        super().__init__(parent)
        self.url = url
        self.method = method
        self.headers = headers or {}
        self.body = body
        self.scanner = SecurityScanner()
        self.scan_worker = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Security Scanner")
        self.setGeometry(200, 200, 900, 700)

        layout = QVBoxLayout()

        header = QLabel("Security Scan Results")
        header_font = QFont()
        header_font.setPointSize(14)
        header_font.setBold(True)
        header.setFont(header_font)
        layout.addWidget(header)

        info_layout = QHBoxLayout()
        info_layout.addWidget(QLabel(f"URL: {self.url}"))
        info_layout.addWidget(QLabel(f"Method: {self.method}"))
        layout.addLayout(info_layout)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.risk_label = QLabel("Risk Score: Not scanned")
        self.risk_label.setFont(QFont("", 10, QFont.Bold))
        layout.addWidget(self.risk_label)

        scan_btn = QPushButton("Run Security Scan")
        scan_btn.clicked.connect(self.run_scan)
        layout.addWidget(scan_btn)

        self.findings_table = QTableWidget()
        self.findings_table.setColumnCount(5)
        self.findings_table.setHorizontalHeaderLabels(["Severity", "Category", "Title", "Description", "Remediation"])
        self.findings_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.findings_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.findings_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        layout.addWidget(self.findings_table)

        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setMaximumHeight(150)
        layout.addWidget(QLabel("Details:"))
        layout.addWidget(self.details_text)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)

        self.setLayout(layout)

        if self.url:
            self.run_scan()

    def run_scan(self):
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.findings_table.setRowCount(0)
        self.details_text.clear()
        self.risk_label.setText("Scanning...")

        self.scan_worker = SecurityScanWorker(
            self.scanner, self.url, self.method, self.headers, self.body
        )
        self.scan_worker.finished.connect(self.on_scan_complete)
        self.scan_worker.error.connect(self.on_scan_error)
        self.scan_worker.start()

    def on_scan_complete(self, report: SecurityReport):
        self.progress_bar.setVisible(False)

        risk_level = get_risk_level(report.risk_score)
        color = self.get_severity_color(report.risk_score)
        self.risk_label.setStyleSheet(f"color: {color}; font-weight: bold;")
        self.risk_label.setText(
            f"Risk Score: {report.risk_score:.1f}/100 ({risk_level}) - "
            f"{report.critical_count} Critical, {report.high_count} High, "
            f"{report.medium_count} Medium, {report.low_count} Low"
        )

        self.findings_table.setRowCount(len(report.findings))
        for row, finding in enumerate(report.findings):
            severity_item = QTableWidgetItem(finding.severity.value.upper())
            severity_item.setBackground(QColor(self.get_severity_bg(finding.severity)))
            severity_item.setForeground(QColor(self.get_severity_fg(finding.severity)))
            self.findings_table.setItem(row, 0, severity_item)
            self.findings_table.setItem(row, 1, QTableWidgetItem(finding.category.value))
            self.findings_table.setItem(row, 2, QTableWidgetItem(finding.title))
            self.findings_table.setItem(row, 3, QTableWidgetItem(finding.description[:100] + "..."))
            self.findings_table.setItem(row, 4, QTableWidgetItem(finding.remediation[:100] + "..."))

        self.findings_table.cellClicked.connect(self.show_details)

    def show_details(self, row, col):
        if 0 <= row < self.findings_table.rowCount():
            findings = []
            for i in range(self.findings_table.rowCount()):
                sev = self.findings_table.item(i, 0).text()
                cat = self.findings_table.item(i, 1).text()
                title = self.findings_table.item(i, 2).text()
                desc = self.findings_table.item(i, 3).text()
                rem = self.findings_table.item(i, 4).text()
                findings.append(f"{sev} | {cat} | {title}\n{desc}\nRemediation: {rem}\n")
            self.details_text.setPlainText("\n---\n".join(findings))

    def on_scan_error(self, error: str):
        self.progress_bar.setVisible(False)
        self.risk_label.setText(f"Error: {error}")

    def get_severity_color(self, severity: Severity) -> str:
        colors = {
            Severity.CRITICAL: "red",
            Severity.HIGH: "orange",
            Severity.MEDIUM: "gold",
            Severity.LOW: "blue",
            Severity.INFO: "gray",
        }
        return colors.get(severity, "black")

    def get_severity_bg(self, severity: Severity) -> str:
        colors = {
            Severity.CRITICAL: "#ffcccc",
            Severity.HIGH: "#ffe0cc",
            Severity.MEDIUM: "#fff2cc",
            Severity.LOW: "#cce5ff",
            Severity.INFO: "#e0e0e0",
        }
        return colors.get(severity, "#ffffff")

    def get_severity_fg(self, severity: Severity) -> str:
        colors = {
            Severity.CRITICAL: "#990000",
            Severity.HIGH: "#995500",
            Severity.MEDIUM: "#666600",
            Severity.LOW: "#003366",
            Severity.INFO: "#333333",
        }
        return colors.get(severity, "#000000")

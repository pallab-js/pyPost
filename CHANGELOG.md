# Changelog

All notable changes to pyPost will be documented in this file.

## [1.0.0] - Current

### Added
- **File Upload Support**: Fixed multipart file uploads - files now properly upload
- **Request Cancellation**: Cancel button to stop ongoing requests
- **Response Pretty-Printing**: Automatic JSON and XML formatting with indentation
- **Syntax Highlighting**: Auto-detection based on response Content-Type
- **History Reload**: Double-click history entries to reload requests
- **Response Size Formatting**: Human-readable format (KB, MB, GB)
- **Dark Mode Persistence**: Dark mode preference saved across sessions
- **Status Code Color Coding**: Visual indicators (green/orange/red/blue)
- **Robust Error Handling**: Better handling of binary responses and edge cases

### Fixed
- **Critical**: Response encoding crashes on binary content
- **Critical**: Race condition in request cancellation
- **Critical**: File upload not working (files passed as strings)
- **High**: Syntax highlighting not activating
- **High**: Resource leaks on cancellation
- **Medium**: Missing error handling for empty/null responses
- **Medium**: Format validation issues
- **Low**: Missing logging import

### Changed
- Updated HTTP worker to use sessions for better resource management
- Improved file handling with proper cleanup in all code paths
- Enhanced error messages for better user feedback
- Better thread safety with proper cancellation handling

### Security
- Encryption for sensitive data (Bearer tokens, Basic Auth)
- Local-first data storage
- SSL verification enabled by default

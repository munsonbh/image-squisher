// image-squisher-automator.js
// JavaScript for Automation script for Automator Folder Action

function run(input, parameters) {
    // Get all folder paths from Automator input
    // Input is an array of file/folder paths
    var folders = input;
    
    // Path to the image-squisher repository
    // Update this path to match your actual repository location
    var scriptDir = '/Users/benmunson/Documents/Repositories/image-squisher';
    
    // Path to Python in virtual environment
    var pythonPath = scriptDir + '/venv/bin/python';
    
    // Path to main.py
    var mainScript = scriptDir + '/main.py';
    
    var app = Application.currentApplication();
    app.includeStandardAdditions = true;
    
    var processedFolders = [];  // Array to hold successfully processed folder paths
    var errors = [];
    
    // Process each folder in the input array
    for (var i = 0; i < folders.length; i++) {
        var folderPath = folders[i];
        
        // Construct the command for this folder
        // Note: main.py processes recursively by default, so each folder will be processed recursively
        var command = 'cd "' + scriptDir + '" && ' + pythonPath + ' "' + mainScript + '" "' + folderPath + '"';
        
        try {
            // Run the command
            var result = app.doShellScript(command);
            // Add the folder path to processedFolders so it can be passed to next action
            processedFolders.push(folderPath);
            
            // Show notification for each folder processed
            app.doShellScript('terminal-notifier -title "Image Squisher" -message "Processing complete for: ' + folderPath + '" 2>/dev/null || true');
        } catch (error) {
            var errorMsg = 'Error processing ' + folderPath + ': ' + error.message;
            errors.push(errorMsg);
            
            // Show error notification
            app.doShellScript('terminal-notifier -title "Image Squisher Error" -message "Error: ' + error.message + '\\nFolder: ' + folderPath + '" 2>/dev/null || true');
        }
    }
    
    // Return the processed folder paths - this allows the next Automator action to use them
    // Note: app.doShellScript() already waits for the Python process to complete
    // before continuing, so this return happens only after all processing is done
    // Returning an array of paths allows Automator to pass them to the next action
    
    if (errors.length > 0) {
        // Log errors but still return processed folders
        app.doShellScript('terminal-notifier -title "Image Squisher" -message "Completed with ' + errors.length + ' error(s). Check logs for details." 2>/dev/null || true');
    }
    
    // Return the array of processed folder paths - this is what the next Automator action needs
    return processedFolders;
}


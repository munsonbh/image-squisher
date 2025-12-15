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
    
    var results = [];
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
            results.push('Processed: ' + folderPath);
            
            // Show notification for each folder processed
            app.doShellScript('terminal-notifier -title "Image Squisher" -message "Processing complete for: ' + folderPath + '" 2>/dev/null || true');
        } catch (error) {
            var errorMsg = 'Error processing ' + folderPath + ': ' + error.message;
            errors.push(errorMsg);
            
            // Show error notification
            app.doShellScript('terminal-notifier -title "Image Squisher Error" -message "Error: ' + error.message + '\\nFolder: ' + folderPath + '" 2>/dev/null || true');
        }
    }
    
    // Return summary
    if (errors.length > 0) {
        return 'Processed ' + results.length + ' folder(s), ' + errors.length + ' error(s).\nErrors:\n' + errors.join('\n');
    } else {
        return 'Successfully processed ' + results.length + ' folder(s).';
    }
}


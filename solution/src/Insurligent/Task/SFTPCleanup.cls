Include %occStatus

/// A Task Manager task: it cleans up the outbox folder of the HIS SFTP server.
/// It deletes the files of the types in FileTypes that are older than Days days,
/// and writes a line to messages.log for each file.
/// The Task Manager shows each property as a setting of the task.
Class Insurligent.Task.SFTPCleanup Extends %SYS.Task.Definition
{

/// The name of this task type in the Task Manager.
Parameter TaskName = "Insurligent SFTP clean-up";

/// The SFTP server. Use his-sftp, not mock_his: the SSH client of IRIS refuses "_" in a host name.
Property Host As %String [ InitialExpression = "his-sftp" ];

Property Port As %Integer [ InitialExpression = 22 ];

/// The ID of the interoperability credentials with the SFTP username and password.
Property Credentials As %String [ InitialExpression = "HIS-SFTP" ];

/// The folder on the SFTP server.
Property Folder As %String(MAXLEN = 200) [ InitialExpression = "/home/his/outbox" ];

/// The file types to delete, separated by commas.
Property FileTypes As %String [ InitialExpression = "pdf,txt" ];

/// Delete a file when it is older than this number of days.
Property Days As %Integer(MINVAL = 1) [ InitialExpression = 7 ];

Method OnTask() As %Status
{
	Set tCred = ##class(Ens.Config.Credentials).%OpenId(..Credentials)
	If '$IsObject(tCred) {
		Return $$$ERROR($$$GeneralError, "No credentials with the ID "_..Credentials)
	}
	Set tSSH = ##class(%Net.SSH.Session).%New()
	// The lab does not check the host key. In production, give the key of the server as the third argument.
	$$$QuitOnError(tSSH.Connect(..Host, ..Port))
	$$$QuitOnError(tSSH.AuthenticateWithUsername(tCred.Username, tCred.Password))
	$$$QuitOnError(tSSH.OpenSFTP(.tSFTP))
	$$$QuitOnError(tSFTP.Dir(..Folder, .tFiles))

	// Dir() gives the times in Unix seconds.
	Set tLimit = $ZDateTime($ZTimeStamp, -2) - (..Days * 86400)
	Set tTypes = ","_$ZConvert(..FileTypes, "L")_","
	Set tDeleted = 0
	Set i = ""
	For {
		Set i = $Order(tFiles(i), 1, tInfo)
		Quit:i=""
		Set tName = $List(tInfo, 1)
		Set tType = $ZConvert($Piece(tName, ".", $Length(tName, ".")), "L")
		Continue:$List(tInfo,3)'="F"
		Continue:tTypes'[(","_tType_",")
		Continue:$List(tInfo,8)>=tLimit
		Set tSC = tSFTP.Delete(..Folder_"/"_tName)
		Return:$$$ISERR(tSC) tSC
		Do ##class(%SYS.System).WriteToConsoleLog("SFTP clean-up: deleted "_..Folder_"/"_tName)
		Set tDeleted = tDeleted + 1
	}
	Do ##class(%SYS.System).WriteToConsoleLog("SFTP clean-up: "_tDeleted_" file(s) deleted from "_..Host_":"_..Folder)
	Do tSSH.Disconnect()
	Return $$$OK
}

}

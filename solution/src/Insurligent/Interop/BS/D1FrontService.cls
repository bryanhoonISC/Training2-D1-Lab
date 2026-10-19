/// Business service (item BS.GetPreAuthInfoView). The REST class Insurligent.REST.Router
/// calls it. It sends the request to the BP in TargetConfigName and waits for the reply.
Class Insurligent.Interop.BS.D1FrontService Extends Ens.BusinessService
{

/// The BP that gets the request.
Property TargetConfigName As Ens.DataType.ConfigName [ InitialExpression = "BP.GetPreAuthInfoView" ];

Parameter SETTINGS = "TargetConfigName:Basic:selector?context={Ens.ContextSearch/ProductionItems?targets=1&productionName=@productionId}";

Method OnProcessInput(pInput As %RegisteredObject, Output pOutput As %RegisteredObject, ByRef pHint As %String) As %Status
{
	Return ..SendRequestSync(..TargetConfigName, pInput, .pOutput, 60)
}

}

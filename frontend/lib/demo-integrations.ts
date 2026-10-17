/** Evidence-qualified catalogue; no credentials, endpoints or synchronization state. */
export const integrations = [
 {id:'files',name:'CSV / XLSX imports',status:'Prototype',data:'Inventory, suppliers, shipments and mapped operational records',method:'File upload and worksheet/column mapping implemented in the authenticated workspace.',evidence:'Local import and reconciliation tests passed. Uploads are not enabled in this public demo; its records are preloaded synthetic examples.',action:'Preview file mapping'},
 {id:'sap',name:'SAP ERP / SAP S/4HANA',status:'Planned',data:'Intended: material stock, purchase orders, suppliers and maintenance requirements',method:'No implemented connection method verified. Product version, APIs and read-only scopes must be assessed.',evidence:'No SAP ERP or S/4HANA adapter found. SAP Business One is a separate product and does not establish S/4HANA support.',action:'View setup requirements'},
 {id:'oracle',name:'Oracle Fusion Cloud ERP',status:'Planned',data:'Intended: inventory, procurement and supplier records; maintenance coverage requires discovery',method:'No implemented connection method verified. Tenant-specific API availability and permissions require assessment.',evidence:'No Oracle Fusion adapter or external synchronization evidence found.',action:'View setup requirements'},
 {id:'b1',name:'SAP Business One',status:'Prototype',data:'Development mappings: business partners → suppliers; items → products; orders → sales orders',method:'Service Layer /b1s/v2 session authentication is implemented in the development adapter; not live-verified.',evidence:'Development branch only; not enabled in this deployed demo. Local mapped-connector tests do not prove external connectivity or inventory/maintenance coverage.',action:'View pilot requirements'},
 {id:'salesforce',name:'Salesforce',status:'Prototype',data:'Deployed adapter: Account / configured objects → supplier records',method:'OAuth token exchange and SOQL are implemented. Customer authorization and live validation remain required.',evidence:'Local synchronization tests only. Wider explicit mappings exist in development; no live customer integration or complete supply-chain coverage is asserted.',action:'View pilot requirements'},
 {id:'bc',name:'Dynamics 365 Business Central',status:'Prototype',data:'Items → products; sales orders → shipment records',method:'OAuth and Business Central API adapter implemented; external execution is not verified.',evidence:'Read mapping code exists. Sales-order records are not proof of physical shipment or delivery. No verified live synchronization.',action:'View pilot requirements'},
] as const;
export const mappingExamples = {
 Inventory: [['Part number','SPARE-1','Product SKU'],['Facility','Plant A','Inventory site'],['Usable quantity','2','Recorded stock'],['Reserved quantity','0','Unavailable commitments']],
 'Purchase order': [['Order / line','PO-1 / 1','Inbound source identity'],['Open quantity','3','Supported inbound quantity'],['Supplier promise','Day 5','Arrival date in simulation'],['Destination','Plant A','Receiving site']],
 Maintenance: [['Work order','WO-A','Requirement identity'],['Required part','SPARE-1','Linked product SKU'],['Required quantity','5','Maintenance demand'],['Required by','Day 3','Readiness deadline']],
 Supplier: [['Supplier reference','SYN-SUP-1','Synthetic supplier identity'],['Supplier name','Synthetic supplier','Supplier record'],['Expedite permission','AUTH-EXPEDITE','Documented action authorization'],['Lead time / cost','1 day / $90 USD','Estimated timing / known direct cost']],
} as const;
export function setupRequirements(id: string): string[] {
 const source=integrations.find(x=>x.id===id);
 if(!source) throw new Error('Unknown integration');
 return [source.status==='Planned'?'Confirm the exact product, API coverage and required read-only records before implementation.':'Provide an authorized test environment and agree the exact records and field mappings.',
 'Use organization-scoped access and server-side encrypted credentials in the authenticated application; never enter secrets into this demo.',
 'Validate endpoint restrictions, pagination, incremental synchronization, duplicate handling and source-to-AtlasOps reconciliation.',
 'Verify disconnect, credential removal and error handling using synthetic test data before customer use.'];
}

/**
 * MunicipalScreen.jsx
 * Services: Property Tax | Trade Licence | Birth Certificate |
 *           Death Certificate | Building Plan | Complaint | Grievance
 */
import ServiceLayout      from './ServiceLayout';
import ServiceRequestForm from './ServiceRequestForm';

const TILES = [
  { action: 'pay_bill',     icon: '🏛️', label: 'Property Tax',        sub: 'Pay municipal property tax'     },
  { action: 'trade_lic',    icon: '📜', label: 'Trade Licence',       sub: 'New or renew trade licence'     },
  { action: 'birth_cert',   icon: '👶', label: 'Birth Certificate',   sub: 'Apply for birth certificate'    },
  { action: 'death_cert',   icon: '📄', label: 'Death Certificate',   sub: 'Apply for death certificate'    },
  { action: 'building',     icon: '🏗️', label: 'Building Plan',       sub: 'Submit building plan approval'  },
  { action: 'complaint',    icon: '🗑️', label: 'Complaint',           sub: 'Report sanitation issue'        },
  { action: 'grievance',    icon: '📣', label: 'Grievance',           sub: 'Submit a general grievance'     },
];

function TradeLicenceForm({ onClose }) {
  return (
    <ServiceRequestForm
      title="Trade Licence"
      icon="📜"
      dept="municipal"
      endpoint="trade-license"
      onClose={onClose}
      fields={[
        { name: 'business_name',  label: 'Business Name',     type: 'text',    placeholder: 'Name of business',       required: true  },
        { name: 'owner_name',     label: 'Owner Name',        type: 'text',    placeholder: 'Full name',              required: true  },
        { name: 'business_type',  label: 'Business Type',     type: 'text',    placeholder: 'e.g. Grocery, Pharmacy', required: true  },
        { name: 'address',        label: 'Business Address',  type: 'textarea',placeholder: 'Full address',           required: true  },
        { name: 'phone',          label: 'Mobile Number',     type: 'tel',     placeholder: '10-digit number',        required: true  },
        { name: 'licence_type',   label: 'Application Type',  type: 'select',  required: true, options: [
            { value: 'new',     label: 'New Licence'    },
            { value: 'renewal', label: 'Renewal'        },
          ]},
        { name: 'existing_no',    label: 'Existing Licence No. (if renewal)', type: 'text', placeholder: 'Leave blank for new', required: false },
      ]}
    />
  );
}

function BirthCertForm({ onClose }) {
  return (
    <ServiceRequestForm
      title="Birth Certificate"
      icon="👶"
      dept="municipal"
      endpoint="birth-certificate"
      onClose={onClose}
      fields={[
        { name: 'child_name',    label: "Child's Full Name",    type: 'text',    placeholder: 'As to appear on certificate', required: true  },
        { name: 'dob',           label: 'Date of Birth',        type: 'date',    placeholder: '',                            required: true  },
        { name: 'father_name',   label: "Father's Name",        type: 'text',    placeholder: 'Full name',                   required: true  },
        { name: 'mother_name',   label: "Mother's Name",        type: 'text',    placeholder: 'Full name',                   required: true  },
        { name: 'hospital_name', label: 'Hospital / Place',     type: 'text',    placeholder: 'Where birth took place',      required: true  },
        { name: 'address',       label: 'Residential Address',  type: 'textarea',placeholder: 'Current address',            required: true  },
        { name: 'phone',         label: 'Mobile Number',        type: 'tel',     placeholder: '10-digit number',            required: true  },
      ]}
    />
  );
}

function DeathCertForm({ onClose }) {
  return (
    <ServiceRequestForm
      title="Death Certificate"
      icon="📄"
      dept="municipal"
      endpoint="death-certificate"
      onClose={onClose}
      fields={[
        { name: 'deceased_name', label: 'Name of Deceased',     type: 'text',    placeholder: 'Full name',              required: true  },
        { name: 'dod',           label: 'Date of Death',        type: 'date',    placeholder: '',                       required: true  },
        { name: 'place_death',   label: 'Place of Death',       type: 'text',    placeholder: 'Hospital or address',    required: true  },
        { name: 'applicant',     label: 'Applicant Name',       type: 'text',    placeholder: 'Your full name',         required: true  },
        { name: 'relation',      label: 'Relation to Deceased', type: 'select',  required: true, options: [
            { value: 'spouse',   label: 'Spouse'   },
            { value: 'child',    label: 'Child'    },
            { value: 'parent',   label: 'Parent'   },
            { value: 'sibling',  label: 'Sibling'  },
            { value: 'other',    label: 'Other'    },
          ]},
        { name: 'phone',         label: 'Mobile Number',        type: 'tel',     placeholder: '10-digit number',        required: true  },
      ]}
    />
  );
}

function BuildingPlanForm({ onClose }) {
  return (
    <ServiceRequestForm
      title="Building Plan Approval"
      icon="🏗️"
      dept="municipal"
      endpoint="building-plan"
      onClose={onClose}
      fields={[
        { name: 'owner_name',    label: 'Property Owner Name',  type: 'text',    placeholder: 'Full name',               required: true  },
        { name: 'plot_no',       label: 'Plot / Survey Number', type: 'text',    placeholder: 'e.g. Plot 45B, Survey 12', required: true  },
        { name: 'address',       label: 'Property Address',     type: 'textarea',placeholder: 'Full address',            required: true  },
        { name: 'plan_type',     label: 'Plan Type',            type: 'select',  required: true, options: [
            { value: 'residential', label: 'Residential'     },
            { value: 'commercial',  label: 'Commercial'      },
            { value: 'mixed',       label: 'Mixed Use'       },
            { value: 'renovation',  label: 'Renovation'      },
          ]},
        { name: 'floors',        label: 'No. of Floors',        type: 'number',  placeholder: 'e.g. 2',                  required: true  },
        { name: 'area_sqft',     label: 'Total Area (sq.ft)',   type: 'number',  placeholder: 'e.g. 1200',               required: true  },
        { name: 'phone',         label: 'Mobile Number',        type: 'tel',     placeholder: '10-digit number',         required: true  },
      ]}
    />
  );
}

function ComplaintForm({ onClose }) {
  return (
    <ServiceRequestForm
      title="Sanitation Complaint"
      icon="🗑️"
      dept="municipal"
      endpoint="complaint"
      onClose={onClose}
      fields={[
        { name: 'consumer_no',   label: 'House No. / Consumer No.', type: 'text',    placeholder: 'Your municipal number',  required: true  },
        { name: 'complaint_type',label: 'Complaint Type',           type: 'select',  required: true, options: [
            { value: 'garbage',    label: 'Garbage not collected'      },
            { value: 'drainage',   label: 'Drainage / Sewage blockage' },
            { value: 'stray',      label: 'Stray animals'              },
            { value: 'road',       label: 'Road damage'                },
            { value: 'other',      label: 'Other sanitation issue'     },
          ]},
        { name: 'location',      label: 'Location / Landmark',     type: 'text',    placeholder: 'Where the issue is',     required: true  },
        { name: 'description',   label: 'Description',             type: 'textarea',placeholder: 'Describe the problem',   required: true  },
        { name: 'phone',         label: 'Mobile Number',           type: 'tel',     placeholder: '10-digit number',        required: true  },
      ]}
    />
  );
}

function GrievanceForm({ onClose }) {
  return (
    <ServiceRequestForm
      title="General Grievance"
      icon="📣"
      dept="municipal"
      endpoint="grievance"
      onClose={onClose}
      fields={[
        { name: 'full_name',     label: 'Your Name',            type: 'text',    placeholder: 'Full name',               required: true  },
        { name: 'phone',         label: 'Mobile Number',        type: 'tel',     placeholder: '10-digit number',         required: true  },
        { name: 'subject',       label: 'Subject',              type: 'text',    placeholder: 'Brief subject line',      required: true  },
        { name: 'department',    label: 'Concerned Department', type: 'select',  required: false, options: [
            { value: 'municipal',    label: 'Municipal Office'   },
            { value: 'water',        label: 'Water Department'   },
            { value: 'electricity',  label: 'Electricity Dept.'  },
            { value: 'roads',        label: 'Roads & Transport'  },
            { value: 'other',        label: 'Other'              },
          ]},
        { name: 'description',   label: 'Grievance Details',    type: 'textarea',placeholder: 'Describe your grievance in detail', required: true },
      ]}
    />
  );
}

const FORM_MODALS = {
  trade_lic:  TradeLicenceForm,
  birth_cert: BirthCertForm,
  death_cert: DeathCertForm,
  building:   BuildingPlanForm,
  complaint:  ComplaintForm,
  grievance:  GrievanceForm,
};

export default function MunicipalScreen() {
  return (
    <ServiceLayout
      dept="municipal"
      icon="🏛️"
      gradient="bg-gradient-to-r from-emerald-500 to-teal-600"
      title="Municipal Services"
      tiles={TILES}
      formModals={FORM_MODALS}
    />
  );
}

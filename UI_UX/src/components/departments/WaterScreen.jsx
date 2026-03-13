/**
 * WaterScreen.jsx
 * Services: Pay Bill | New Connection | Leak Complaint
 */
import ServiceLayout      from './ServiceLayout';
import ServiceRequestForm from './ServiceRequestForm';

const TILES = [
  { action: 'pay_bill',    icon: '💳', label: 'Pay Bill',        sub: 'Pay your water bill'          },
  { action: 'new_conn',    icon: '🔗', label: 'New Connection',  sub: 'Apply for new water supply'   },
  { action: 'leak',        icon: '🚰', label: 'Report Leak',     sub: 'Report a water leak'          },
];

function NewConnectionForm({ onClose }) {
  return (
    <ServiceRequestForm
      title="New Water Connection"
      icon="🔗"
      dept="water"
      endpoint="new-connection"
      onClose={onClose}
      fields={[
        { name: 'full_name',   label: 'Full Name',         type: 'text',     placeholder: 'e.g. Priya Devi',       required: true  },
        { name: 'address',     label: 'Property Address',  type: 'textarea', placeholder: 'Full address with pin',  required: true  },
        { name: 'phone',       label: 'Mobile Number',     type: 'tel',      placeholder: '10-digit number',        required: true  },
        { name: 'property_type', label: 'Property Type',  type: 'select',   required: true, options: [
            { value: 'residential', label: 'Residential' },
            { value: 'commercial',  label: 'Commercial'  },
            { value: 'industrial',  label: 'Industrial'  },
          ]},
        { name: 'id_proof',    label: 'ID Proof Type',    type: 'select',   required: true, options: [
            { value: 'aadhaar',    label: 'Aadhaar Card' },
            { value: 'voter',      label: 'Voter ID'     },
            { value: 'passport',   label: 'Passport'     },
          ]},
        { name: 'id_number',   label: 'ID Number',        type: 'text',     placeholder: 'ID document number',    required: true  },
      ]}
    />
  );
}

function LeakComplaintForm({ onClose }) {
  return (
    <ServiceRequestForm
      title="Report Water Leak"
      icon="🚰"
      dept="water"
      endpoint="leak-complaint"
      onClose={onClose}
      fields={[
        { name: 'consumer_no', label: 'Consumer Number',  type: 'text',     placeholder: 'e.g. WTR-2204-001',     required: true  },
        { name: 'location',    label: 'Leak Location',    type: 'text',     placeholder: 'e.g. Near meter, street outside house', required: true },
        { name: 'severity',    label: 'Severity',         type: 'select',   required: true, options: [
            { value: 'high',   label: '🔴 High — broken pipe / no supply' },
            { value: 'medium', label: '🟡 Medium — steady leak'           },
            { value: 'low',    label: '🟢 Low — slow drip'               },
          ]},
        { name: 'description', label: 'Description',     type: 'textarea', placeholder: 'Describe the issue in detail', required: false },
      ]}
    />
  );
}

const FORM_MODALS = {
  new_conn: NewConnectionForm,
  leak:     LeakComplaintForm,
};

export default function WaterScreen() {
  return (
    <ServiceLayout
      dept="water"
      icon="💧"
      gradient="bg-gradient-to-r from-blue-500 to-cyan-500"
      title="Water Services"
      tiles={TILES}
      formModals={FORM_MODALS}
    />
  );
}

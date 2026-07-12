# MVP Permission Matrix

Legend: `G` global, `O` organization, `S` school, `T` own teaching assignment, `-` denied.

| Capability | System admin | Organization manager | School manager | Academic deputy | Operator | Teacher |
|---|---:|---:|---:|---:|---:|---:|
| Manage organizations | G | O | - | - | - | - |
| Manage schools | G | O | S read | S read | S read | T read |
| Manage users/memberships | G | O | S | S read | - | - |
| Manage academic structure | G | O | S | S | S | T read |
| Manage students/guardians | G | O | S | S | S | T read |
| Manage enrollments/transfers | G | O | S | S | S | T read |
| Manage course offerings | G | O | S | S | S limited | T read |
| Enter scores | G | O | S | S | policy-based | T only |
| Submit scores | G | O | S | S | policy-based | T only |
| Reject/approve/lock scores | G | O | S | S | - | - |
| Override locked score | G | explicit | explicit | explicit | - | - |
| Generate/download reports | G | O | S | S | S limited | T limited |
| View audit | G | O | S limited | S limited | own actions | own actions |

Every cell is further constrained by active membership, academic year, class, course offering and object ownership. Slice 1 will encode named policies rather than role-name checks in views.

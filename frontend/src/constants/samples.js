/**
 * Curated sample prompts and code snippets for instant testing and demonstration.
 */

export const SAMPLE_PROMPTS = [
  {
    id: 'auth_flow',
    title: 'User Login & Auth Workflow',
    type: 'flowchart',
    text: 'User submits login form. If credentials valid, issue JWT and redirect to dashboard; otherwise increment retry count and show error.',
  },
  {
    id: 'microservices_arch',
    title: 'E-Commerce Cloud Architecture',
    type: 'architecture',
    text: 'React Web App calls API Gateway, which routes requests to Order Service and Payment Service. Order Service queries Postgres database and reads from Redis cache.',
  },
  {
    id: 'ml_concept_map',
    title: 'Machine Learning Concepts',
    type: 'concept_map',
    text: 'Artificial Intelligence encompasses Machine Learning. Machine Learning divides into Supervised Learning and Unsupervised Learning. Neural Networks form the foundation of Deep Learning.',
  },
  {
    id: 'checkout_sequence',
    title: '2-Factor Authentication Flow',
    type: 'sequence_diagram',
    text: 'Client submits login credentials to Auth Server. Auth Server validates user in User Database, sends OTP to SMS Gateway, and SMS Gateway delivers OTP to Client.',
  },
  {
    id: 'hospital_er',
    title: 'Hospital Database ER Schema',
    type: 'er_diagram',
    text: 'Doctor treats Patient with 1:N cardinality. Patient receives Prescription with 1:N cardinality. Doctor writes Prescription with 1:N cardinality.',
  },
  {
    id: 'office_network',
    title: 'Enterprise Branch Network',
    type: 'network_topology',
    text: 'Core Switch connects to Firewall, File Server, Database Server, and two Workstations on the corporate subnet.',
  },
  {
    id: 'ci_cd_pipeline',
    title: 'Software Release Build DAG',
    type: 'dependency_graph',
    text: 'Lint Code and Run Unit Tests run first. Build Docker Image depends on Lint Code and Unit Tests. Deploy to Staging depends on Build Docker Image.',
  },
];

export const SAMPLE_CODE_SNIPPETS = [
  {
    id: 'factorial_rec',
    title: 'Recursive Factorial',
    code: `def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)

result = factorial(3)
print("Factorial result:", result)
`,
  },
  {
    id: 'bubble_sort',
    title: 'Bubble Sort Algorithm',
    code: `arr = [5, 2, 8, 1]
n = len(arr)

for i in range(n):
    for j in range(0, n - i - 1):
        if arr[j] > arr[j + 1]:
            arr[j], arr[j + 1] = arr[j + 1], arr[j]

print("Sorted array:", arr)
`,
  },
  {
    id: 'discount_calc',
    title: 'Conditional Discount Logic',
    code: `cart_total = 120.0
discount = 0.0

if cart_total > 100.0:
    discount = 0.15
    final_price = cart_total * (1.0 - discount)
else:
    final_price = cart_total

print("Final price:", final_price)
`,
  },
  {
    id: 'while_counter',
    title: 'While Loop Accumulator',
    code: `total = 0
count = 1

while count <= 4:
    total += count * 10
    count += 1

print("Total accumulated:", total)
`,
  },
];

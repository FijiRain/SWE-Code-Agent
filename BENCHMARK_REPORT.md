
# Consignes :

You must produce a benchmark report comparing at least 5 models across at least 2 providers on the same set of at least 3 SWE-bench tasks.

## Setup: 

Which models/providers were compared, which tasks were used, and why those tasks were selected

## Results table: 

For each model × task combination:
• Pass/Fail
• Iterations used
• Total input tokens
• Total output tokens
• Wall-clock time

## Provider reliability: 

For each model/provider:
• Average response time per request
• Number of retries needed (rate limits, timeouts, errors)
• Overall availability during benchmark runs

## Intermediary metrics (at least 2 of the following):

• Step at which the agent first reads/edits the file that appears in the final patch
(exploration efficiency)
• Step at which test failures first decrease vs baseline (partial progress)
• Iterations between “tests first pass” and final_answer (submission discipline — zero is ideal)

These metrics can be measured manually by inspecting your solution.json files
— automation is not required. What matters is the analysis, not the tooling.

## Ablation study: 

At least one before/after comparison of a change to your agent
(prompt, tools, parameters) on the same tasks with the same model

## Conclusions: 

Which model(s) you selected for your final pipeline and why. Which
models can be disregarded and why. Based on your data.

The backing solution.json files must be present in your repository.


_______________________

Groq: uv run python3 -m agent_mbpp --task-file tests/test_mbpp_task.json --output tests/mbpp_solution.json --model-name "" --provider-url "https://api.groq.com/openai/v1/"

OpenRouter: uv run python3 -m agent_mbpp --task-file tests/test_mbpp_task.json --output tests/mbpp_solution.json --model-name "" --provider-url "https://openrouter.ai/api/v1"

Google AI Studio: uv run python3 -m agent_mbpp --task-file tests/test_mbpp_task.json --output tests/mbpp_solution.json --model-name "" --provider-url "https://generativelanguage.googleapis.com/v1beta/openai/"

# MBPP (task 128):

## Google:

gemini-3-flash-preview : 

  "iterations": 3,
  "total_requests": 3,
  "total_input_tokens": 4282,
  "total_output_tokens": 650,
  "total_time_seconds": 7.871476888656616,

gemini-3.1-flash-lite-preview :

  "iterations": 2,
  "total_requests": 2,
  "total_input_tokens": 2448,
  "total_output_tokens": 262,
  "total_time_seconds": 4.348650932312012,

## Groq

qwen/qwen3.8-27b :

  "iterations": 2,
  "total_requests": 2,
  "total_input_tokens": 2380,
  "total_output_tokens": 219,
  "total_time_seconds": 1.775547981262207,

openai/gpt-oss-20b (**FAIL**):

"error": "Unrecoverable client error (400): {\"error\":{\"message\":\"Tool choice is none, but model called a tool\",\"type\":\"invalid_request_error\",\"code\":\"tool_use_failed\",\"failed_generation

openai/gpt-oss-120b (top swe) :

  "iterations": 2,
  "total_requests": 2,
  "total_input_tokens": 2398,
  "total_output_tokens": 518,
  "total_time_seconds": 5.684346914291382,


## OpenRouter
# (le plus lent)

cohere/north-mini-code:free (**FAIL**):

  "iterations": 2,
  "total_requests": 2,
  "total_input_tokens": 2200,
  "total_output_tokens": 1909, <= **FAILED**
  "total_time_seconds": 17.83266305923462,


nvidia/nemotron-3-ultra-550b-a55b:free :

  "iterations": 3,
  "total_requests": 3,
  "total_input_tokens": 3868,
  "total_output_tokens": 670,
  "total_time_seconds": 22.16216802597046,

## Test moulinette MBPP:

Groq - qwen3.8-27b :

- task 447 ok

  "solution": "def cube_nums(nums):\n    cube = lambda x: x ** 3\n    return list(map(cube, nums))",
  "iterations": 3,
  "total_requests": 3,
  "total_input_tokens": 3720,
  "total_output_tokens": 264,
  "total_time_seconds": 2.571532964706421,

- task 284 ok

  "solution": "def check_element(list, element):\n    return all(item == element for item in list)\n",
  "iterations": 2,
  "total_requests": 2,
  "total_input_tokens": 2272,
  "total_output_tokens": 153,
  "total_time_seconds": 1.5597517490386963,

- task 18 ok

  "solution": "def remove_dirty_chars(string, second_string):\n    second_set = set(second_string)\n    return ''.join(char for char in string if char not in second_set)\n",
  "iterations": 2,
  "total_requests": 2,
  "total_input_tokens": 2373,
  "total_output_tokens": 238,
  "total_time_seconds": 2.0235440731048584,

- task 96 ok 

  "solution": "def divisor(n):\n    n = abs(n)\n    count = 0\n    for i in range(1, int(n**0.5) + 1):\n        if n % i == 0:\n            count += 1\n            if i != n // i:\n                count += 1\n    return count",
  "iterations": 3,
  "total_requests": 3,
  "total_input_tokens": 3838,
  "total_output_tokens": 504,
  "total_time_seconds": 4.1931469440460205,

- task 223 ok 

  "solution": "def is_majority(arr, n, x):\n    # Find the first occurrence of x\n    low, high = 0, n - 1\n    first = -1\n    while low <= high:\n        mid = (low + high) // 2\n        if arr[mid] == x:\n            first = mid\n            high = mid - 1\n        elif arr[mid] < x:\n            low = mid + 1\n        else:\n            high = mid - 1\n            \n    if first == -1:\n        return False\n        \n    # Find the last occurrence of x\n    low, high = 0, n - 1\n    last = -1\n    while low <= high:\n        mid = (low + high) // 2\n        if arr[mid] == x:\n            last = mid\n            low = mid + 1\n        elif arr[mid] < x:\n            low = mid + 1\n        else:\n            high = mid - 1\n            \n    # Count the occurrences\n    count = last - first + 1\n    \n    # Check if the count is strictly greater than n/2\n    return count > n // 2\n",
  "iterations": 3,
  "total_requests": 3,
  "total_input_tokens": 4458,
  "total_output_tokens": 988,
  "total_time_seconds": 3.6450488567352295,

- task 256 

  "solution": "def count_Primes_nums(n):\n    def is_prime(num):\n        if num < 2:\n            return False\n        for i in range(2, int(num**0.5) + 1):\n            if num % i == 0:\n                return False\n        return True\n    \n    count = 0\n    for num in range(2, n):\n        if is_prime(num):\n            count += 1\n    return count",
  "iterations": 3,
  "total_requests": 3,
  "total_input_tokens": 4135,
  "total_output_tokens": 670,
  "total_time_seconds": 34.78450107574463,

- task 253 

  "solution": "def count_integer(list1):\n    count = 0\n    for item in list1:\n        if isinstance(item, int) and not isinstance(item, bool):\n            count += 1\n    return count",
  "iterations": 3,
  "total_requests": 3,
  "total_input_tokens": 3589,
  "total_output_tokens": 312,
  "total_time_seconds": 2.7660889625549316,

- task 296

  "solution": "\ndef get_Inv_Count(arr):\n    if not arr:\n        return 0\n    \n    def merge_sort_and_count(arr, l, m, r):\n        left = arr[l:m+1]\n        right = arr[m+1:r+1]\n        \n        i = j = 0\n        k = l\n        count = 0\n        \n        while i < len(left) and j < len(right):\n            if left[i] <= right[j]:\n                arr[k] = left[i]\n                i += 1\n            else:\n                arr[k] = right[j]\n                j += 1\n                count += len(left) - i\n            k += 1\n        \n        while i < len(left):\n            arr[k] = left[i]\n            i += 1\n            k += 1\n            \n        while j < len(right):\n            arr[k] = right[j]\n            j += 1\n            k += 1\n            \n        return count\n\n    def sort_and_count(arr, l, r):\n        count = 0\n        if l < r:\n            m = (l + r) // 2\n            count += sort_and_count(arr, l, m)\n            count += sort_and_count(arr, m+1, r)\n            count += merge_sort_and_count(arr, l, m, r)\n        return count\n\n    arr_copy = arr.copy()\n    return sort_and_count(arr_copy, 0, len(arr_copy) - 1)\n",
  "iterations": 2,
  "total_requests": 2,
  "total_input_tokens": 2562,
  "total_output_tokens": 855,
  "total_time_seconds": 9.856165170669556,

- task 290 

  "solution": "def max_length(list1):\n    max_len = max(len(lst) for lst in list1)\n    max_lst = next(lst for lst in list1 if len(lst) == max_len)\n    return (max_len, max_lst)\n",
  "iterations": 4,
  "total_requests": 4,
  "total_input_tokens": 5329,
  "total_output_tokens": 429,
  "total_time_seconds": 19.784922122955322,

- task 129

FAIL !

  "solution": "", <= Correctness check detail: Traceback(most recent call last): File "<string>", line 2, i<module>

NameError: name 'magic_square_test' is not defined
  "iterations": 4,
  "total_requests": 4,
  "total_input_tokens": 7291, <= FAIL
  "total_output_tokens": 1187,
  "total_time_seconds": 48.73417401313782,

Note : Qwen a halluciné et a mis une balise </think> parasite qui a détruit le reste de l'extraction






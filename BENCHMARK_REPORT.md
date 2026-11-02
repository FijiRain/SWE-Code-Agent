# Test MBPP sur une même task (numéro 128) et différents LLM:

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

FAIL ! (patched 29/10/26)

  "solution": "", <= Correctness check detail: Traceback(most recent call last): File "<string>", line 2, i<module>

NameError: name 'magic_square_test' is not defined
  "iterations": 4,
  "total_requests": 4,
  "total_input_tokens": 7291, <= FAIL
  "total_output_tokens": 1187,
  "total_time_seconds": 48.73417401313782,

Note : Qwen a halluciné et a mis une balise </think> parasite qui a détruit le reste de l'extraction

______________________________________________________

## Agent execution commands:

Groq: uv run python3 -m agent_mbpp --task-file tests/test_mbpp_task.json --output tests/mbpp_solution.json --model-name "" --provider-url "https://api.groq.com/openai/v1/"

OpenRouter: uv run python3 -m agent_mbpp --task-file tests/test_mbpp_task.json --output tests/mbpp_solution.json --model-name "" --provider-url "https://openrouter.ai/api/v1"

Google AI Studio: uv run python3 -m agent_mbpp --task-file tests/test_mbpp_task.json --output tests/mbpp_solution.json --model-name "" --provider-url "https://generativelanguage.googleapis.com/v1beta/openai/"

# Real benchmark SWE:

Intro et definition des termes du benchmark.

First read/edit on the codebase = exploration efficiency

Submission discipline = when tests passed, how many steps until the agent submit final_answer() without useless or parasite iterations. 0 is ideal

# 1st task - sympy__sympy-14711:

This task was chosen because the subject noticed that it's the easiest one. So it is perfect to benchmark plenty of models in order to select the better ones.

## Provider: Groq

### Model: openai/gpt-oss-120b

PASSED
Iterations: 4 / 30
Input tokens: 16243 / 300000
Output tokens: 1389 / 10000
Time: 55.7s / 900.0s
Avg response time/request: 12203.7 ms (12.20s)
Total retries: 0
Availability: 100% (4 steps + 0 retries)
First read/edit on the codebase: @ 2nd step
Submission discipline: 0

### Model: qwen/qwen3.8-27b

First test:

PASSED but...
Iterations: 10 / 30
Input tokens: 46075 / 300000
Output tokens: 896 / 10000
Time: 342.7s / 900.0s
Avg response time/request: 33406.9 ms (33.41s)
Total retries: 0
Availibility: 100% (10 steps + 0 retries)
First read/edit on the codebase: @ 1st step
Submission discipline: N/A, see note

Notes: Orchestrator architecture saved this test! Model has been interrupted at step 10 because it exceed the Groq max tokens/minute. "force_swe_patch()" method in orchestrator.py forced the agent to generate a patch and saved the task! Because Qwen did the task well, it was just interrupted by Groq server (HTTP 413).

Second test: same event...

Third test (patch 413 errors to rotate API key in orchestrator.py):

PASSED
Iterations: 4 / 30
Input tokens: 15645 / 300000
Output tokens: 289 / 10000
Time: 77.4s / 900.0s
Avg response time/request: 17885.7 ms (17.89s)
Total retries: 0
Availibility: 100% (4 steps + 0 retries)
First read/edit on the codebase: @ 1st step
Submission discipline: 0

## Provider: Openrouter

### Model: nvidia/nemotron-3-ultra-550b-a55b:free

FAILED
Iterations: 30 / 30 EXCEEDED
Input tokens: 211860 / 300000
Output tokens: 3339 / 10000
Time: 122.8s / 900.0s
Avg Response Time: 3672.7 ms (3.67s)
Total retries: 0
Availibility: 96.8% (30 steps + 1 retries)
First read/edit on the codebase: @ 2nd step
Submission discipline: N/A (task failed)

Notes: Nemotron **atrociously** failed the simplest SWE benchmark task... It tried to make a patch with an incorrect Python version, then was persuaded there was a SymPy issue so it uninstalled it. Then it patched the wrong file...

### Model: dots-studio/dots-3-note-preview:free

FAILED
Iterations: 25 / 30
Input tokens: 92499 / 300000
Output tokens: 23303 / 10000
Time: 270.8s / 900.0s
Avg Response Time: 10712.9 ms (10.71s)
Total retries: 1
Availibility: 96.2% (25 steps + 1 retries)
First read/edit on the codebase: Model never tried to read_files...
Submission discipline: N/A (task failed)

Notes: Model kept hallucinating and enjoyed being extremely stubborn by not using any tools and put "think" brackets everywhere.

### Model: nvidia/nemotron-3.5-super-vl:free

PASSED
Iterations: 24 / 30
Input tokens: 167037 / 300000
Output tokens: 6454 / 10000
Time: 132.1s / 900.0s
Avg Response Time: 4891.4 ms (4.89s)
Total retries: 1
Availibility: 96.0% (24 steps + 1 retries)
First read/edit on the codebase: @ 1st step
Submission discipline: 0

### Model: cohere/north-mini-code:free

FAILED
Iterations: 1 / 30
Input tokens: 2834 / 300000
Output tokens: 21088 / 10000 EXCEEDED
Time: 205.8s / 900.0s
Avg Response Time: 200664.5 ms (200.66s)
Total retries: 2
Availibility: 33.3% (1 steps + 2 retries)
First read/edit on the codebase: N/A
Submission discipline: N/A

Notes: the model refused to follow ReAct format and kept hallucinating Observations results.

## Provider: Google AI Studio

### Model: gemini-3.1-flash-lite-preview

PASSED
Iterations: 19 / 30
Input tokens: 135416 / 300000
Output tokens: 1606 / 10000
Time: 44.0s / 900.0s
Avg Response Time: 1667.5 ms (1.67s)
Total retries: 1
Availibility: 95.0% (19 steps + 1 retries)
First read/edit on the codebase: @ 1st step
Submission discipline: 0

### Model: gemini-3-flash-preview

FAILED - TIME OUT
No solution submitted...

### Model: gemini-3.5-flash-lite

FAILED
Iterations: 30 / 30 EXCEEDED
Input tokens: 293575 / 300000
Output tokens: 4743 / 10000
Time: 53.1s / 900.0s
Avg Response Time: 1422.6 ms (1.42s)
Total retries: 1
Availibility: 96.8% ((30 steps + 1 retries))
First read/edit on the codebase: @ 2nd step
Submission discipline: N/A

Notes: model suffered from an exploration paralysis syndrom: it kept inspecting files without making "edit_file()" tool, so it reached the 30 iterations limit.

# 2nd task - pydata__xarray-4629 :

This task is pertinent for our agent because the LLM is now challenged on a different paradigm: a data analysis issue.

According to the previous tests, it's pointless to try unqualified models that not passed the previous task into an harder SWEbench one. Given that only 4 models passed the previous tests and that we need 5 models to test, the decision was made to keep a really quick but inefficient model: gemini-3.5-flash-lite.
So here the top qualified models selected for this next task, ranked by efficiency:

- openai/gpt-oss-120b (Groq);
- qwen/qwen3.8-27b (Groq);
- gemini-3.1-flash-lite-preview (Google AI Studio);
- nvidia/nemotron-3.5-super-v1:free (OpenRouter);
- gemini-3.5-flash-lite (Google AI Studio)

## Provider: Groq

### Model: openai/gpt-oss-120b

PASSED
Iterations: 8 / 30
Input tokens: 44983 / 300000
Output tokens: 1028 / 10000
Time: 138.9s / 900.0s
Avg Response Time: 15073.6 ms (15.07s)
Total retries: 0
Availibility: 100% (8 steps + 0 retries)
First read/edit on the codebase: @ 2nd step
Submission discipline: 0

### Model: qwen/qwen3.8-27b

PASSED
Iterations: 5 / 30
Input tokens: 26993 / 300000
Output tokens: 348 / 10000
Time: 361.0s / 900.0s
Avg Response Time: 32728.1 ms (32.73s)
Total retries: 0
Availibility: 100% (5 steps + 0 retries)
First read/edit on the codebase: @ 1st step
Submission discipline: 0

## Provider: OpenRouter

### Model: nvidia/nemotron-3.5-super-v1:free

PASSED
Iterations: 5 / 30
Input tokens: 23724 / 300000
Output tokens: 642 / 10000
Time: 69.8s / 900.0s
Avg Response Time: 1814.5 ms (1.81s)
Total retries: 2
Availibility: 71,4% (5 steps + 2 retries)
First read/edit on the codebase: @ 1st step
Submission discipline: 0

## Provider: Google AI Studio

### Model: gemini-3.1-flash-lite-preview

PASSED
Iterations: 8 / 30
Input tokens: 46059 / 300000
Output tokens: 1121 / 10000
Time: 28.4s / 900.0s
Avg Response Time: 2717.7 ms (2.72s)
Total retries: 0
Availibility: 100% (8 steps + 0 retries)
First read/edit on the codebase: @ 1st step
Submission discipline: 0

### Model: gemini-3.5-flash-lite

PASSED
Iterations: 6 / 30
Input tokens: 34700 / 300000
Output tokens: 360 / 10000
Time: 17.7s / 900.0s
Avg Response Time: 1338.6 ms (1.34s)
Total retries: 0
Availibility: 100% (6 steps + 0 retries)
First read/edit on the codebase: @ 1st step
Submission discipline: 0

# 3rd task - django__django-11066:

This advanced task is perfect to push the limits of our models with a new paradigm (web back end). The task is what an IRL bug in a production chain can look like.

## Provider: Groq

### Model: openai/gpt-oss-120b

FAILED
Iterations: 5 / 30
Input tokens: 27578 / 300000
Output tokens: 4091 / 10000
Time: 244.1s / 900.0s
Avg Response Time: 15152.1 ms (15.15s)
Total retries: 2
Availibility: 71.4% (5 steps + 2 retries)
First read/edit on the codebase: @ 2nd step
Submission discipline: N/A

### Model: qwen/qwen3.8-27b

PASSED
Iterations: 11 / 30
Input tokens: 61894 / 300000
Output tokens: 677 / 10000
Time: 662.0s / 900.0s
Avg Response Time: 37590.9 ms (37.59s)
Total retries: 1
Availibility: 91.7% (11 steps + 1 retries)
First read/edit on the codebase: @ 2nd step
Submission discipline: N/A

Notes: Solution saved by the agent architecture which use "force_swe_patch()" after an exhausted API keys error.

## Provider: OpenRouter

### Model: nvidia/nemotron-3.5-super-v1:free

PASSED
Iterations: 4 / 30
Input tokens: 20700 / 300000
Output tokens: 553 / 10000
Time: 75.7s / 900.0s
Avg Response Time: 2336.0 ms (2.34s)
Total retries: 2
Availibility: 100% (4 steps + 2 retries)
First read/edit on the codebase: @ 1st step
Submission discipline: 0

## Provider: Google AI Studio

### Model: gemini-3.1-flash-lite-preview

PASSED
Iterations: 7 / 30
Input tokens: 44397 / 300000
Output tokens: 934 / 10000
Time: 49.0s / 900.0s
Avg Response Time:  5061.4 ms (5.06s)
Total retries: 0
Availibility: 100% (7 steps + 0 retries)
First read/edit on the codebase: @ 1st step
Submission discipline: 0

### Model: gemini-3.5-flash-lite

PASSED
Iterations: 9 / 30
Input tokens: 52167 / 300000
Output tokens: 509 / 10000
Time: 14.5s / 900.0s
Avg Response Time: 1200.4 ms (1.20s)
Total retries: 0
Availibility: 100% (9 steps + 0 retries)
First read/edit on the codebase: @ 3rd step
Submission discipline: 1

## Ablation Study 

Parler de quand gpt-oss-120b partait en monologue infini de 3000 tokens et sortait un patch vide, il fallait rajouter \```Thought au stop sequence du LLM pour l'empecher d'halluciner en boucle

## Conclusion

Based on the current benchmark, we can conclude that the top models that are being selected for our final pipeline are:

- 
- 
-
# Demo walkthrough

About 5 minutes. Start the system first, as in the README. Works with no AI key.

**Learner**

1. Open http://127.0.0.1:5173 and press **Try as a learner**. Note the label saying it is not a secure account.
2. Choose "I'm brand new", then **Start learning**. Home recommends **Say Hello**, and says why.
3. Press **Start**. Point out the short walkthrough, the examples and the three separate actions.
4. Press **Run** with the starter code. It is not graded, and the example shows expected and actual values.
5. Replace the code with `def greet(name): return "Hello " + name`, and watch the "earlier version" label appear on the old results.
6. Press **Submit**. Show the order: what happened, next action, tests. In the Tutor panel, open **Why this hint?**
7. Press **Submit** again after adding a comment, to show the same issue escalating by one step, with the reason.
8. Press **I need more help**, then show that nothing else happens until you act.
9. Fix it with `def greet(name): return f"Hello, {name}!"` and **Submit**. Show the reflection question and the next step. It suggests similar practice, not advancing after one success.
10. Open **Progress**. Show ranges rather than exact scores, the "What does this estimate mean?" explanation, and that measured improvement is unavailable without both checks.

**Add a question**

11. Go to **Problems**, then **Add question**, then **Paste details**. Paste:

    ```text
    Two Sum
    Easy
    Given an array of integers nums and an integer target, return indices of the two numbers that add up to target.

    Example 1:
    Input: nums = [2,7,11,15], target = 9
    Output: [0,1]

    Constraints:
    2 <= nums.length <= 500
    ```
12. Review the extracted details. On the tests step, show the "not the original platform's hidden tests" note and the generated tests that stay off until given an answer. Save, then submit a wrong answer to show the same tutor at work.
13. Try **Import from a link** with a LeetCode URL for the explanation, then with `1872A` to see Codeforces metadata.

**Teacher**

14. Sign out, then **Try as a teacher**. Show the synthetic-data warning, the formulas, the learners flagged with evidence and uncertainty, and common errors.

**Engineering**

15. Show failure handling by stopping the execution service and pressing **Run**. The app says it is a problem on its side, and your code stays. Restart it and try again.
16. Open `http://127.0.0.1:8101/api/docs` for the API, and `backend/app/tutoring/policy.yaml` to show DSDA's settings.

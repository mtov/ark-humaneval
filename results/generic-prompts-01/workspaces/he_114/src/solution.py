
def minSubArraySum(nums):
    """
    Given an array of integers nums, find the minimum sum of any non-empty sub-array
    of nums.
    Example
    minSubArraySum([2, 3, 4, 1, 2, 4]) == 1
    minSubArraySum([-1, -2, -3]) == -6
    """
    min_ending_here = min_so_far = nums[0]
    for num in nums[1:]:
        min_ending_here = min(num, min_ending_here + num)
        min_so_far = min(min_so_far, min_ending_here)
    return min_so_far

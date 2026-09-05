pub const FORMAT_VERSION: u32 = 1;

#[cfg(test)]
mod tests {
    #[test]
    fn version_one() {
        assert_eq!(super::FORMAT_VERSION, 1);
    }
}
